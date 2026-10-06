from __future__ import annotations

import json,re,unicodedata
from collections import defaultdict,deque
from dataclasses import dataclass
from datetime import datetime,timezone
from pathlib import Path
from typing import Any
import httpx,joblib,numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score,log_loss
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

FEATURE_NAMES=["home_ppg_5","away_ppg_5","home_ppg_10","away_ppg_10","home_venue_ppg_5","away_venue_ppg_5","home_gf_5","away_gf_5","home_ga_5","away_ga_5","home_gd_10","away_gd_10","home_elo","away_elo","elo_diff"]
SEASONS=("2022-23","2023-24","2024-25","2025-26","2026-27")
LEAGUES={"epl":{"name":"Premier League","file":"en.1.json"},"laliga":{"name":"La Liga","file":"es.1.json"},"bundesliga":{"name":"Bundesliga","file":"de.1.json"},"seriea":{"name":"Serie A","file":"it.1.json"},"ligue1":{"name":"Ligue 1","file":"fr.1.json"}}
DATA_URL="https://raw.githubusercontent.com/openfootball/football.json/master/{season}/{file}"
C_VALUES=(0.05,0.1,0.2,0.35,0.5,0.8,1.0)
@dataclass
class TeamState:elo:float=1500.
def normalize_team_name(name:str)->str:
 s=unicodedata.normalize("NFKD",name).encode("ascii","ignore").decode().casefold();s=re.sub(r"\b(fc|cf|afc|calcio|football club|futbol club|club de futbol)\b"," ",s);return re.sub(r"[^a-z0-9]+","",s)
def _avg(v,default=1.35):return sum(v)/len(v) if v else default

def download_rows(key:str)->list[dict[str,Any]]:
 cfg=LEAGUES[key];rows=[]
 with httpx.Client(timeout=30.,follow_redirects=True,headers={"User-Agent":"FanSphere-ML/3.0"}) as client:
  for season in SEASONS:
   r=client.get(DATA_URL.format(season=season,file=cfg["file"]));r.raise_for_status();count=0
   for m in r.json().get("matches",[]):
    score=m.get("score");ft=score.get("ft") if isinstance(score,dict) else None
    if not isinstance(ft,list) or len(ft)!=2:continue
    try:hg,ag=int(ft[0]),int(ft[1])
    except (TypeError,ValueError):continue
    rows.append({"date":m.get("date",season),"home":m.get("team1",""),"away":m.get("team2",""),"hg":hg,"ag":ag,"season":season});count+=1
   print(f"{cfg['name']} {season}: {count} completed matches")
 rows.sort(key=lambda r:r["date"]);return rows

def build_examples(rows):
 state=defaultdict(TeamState);points5=defaultdict(lambda:deque(maxlen=5));points10=defaultdict(lambda:deque(maxlen=10));homepoints5=defaultdict(lambda:deque(maxlen=5));awaypoints5=defaultdict(lambda:deque(maxlen=5));gf5=defaultdict(lambda:deque(maxlen=5));ga5=defaultdict(lambda:deque(maxlen=5));gd10=defaultdict(lambda:deque(maxlen=10));x=[];y=[];meta=[]
 for r in rows:
  h,a,hg,ag=r["home"],r["away"],r["hg"],r["ag"]
  if len(points5[h])>=3 and len(points5[a])>=3:
   he,ae=state[h].elo,state[a].elo
   x.append([_avg(points5[h]),_avg(points5[a]),_avg(points10[h]),_avg(points10[a]),_avg(homepoints5[h]),_avg(awaypoints5[a]),_avg(gf5[h]),_avg(gf5[a]),_avg(ga5[h]),_avg(ga5[a]),_avg(gd10[h],0.),_avg(gd10[a],0.),he,ae,he-ae])
   y.append("HOME" if hg>ag else "AWAY" if ag>hg else "DRAW");meta.append({"date":r["date"],"season":r["season"],"home":h,"away":a})
  result="HOME" if hg>ag else "AWAY" if ag>hg else "DRAW";hp,ap=(3.,0.) if result=="HOME" else ((1.,1.) if result=="DRAW" else (0.,3.))
  points5[h].append(hp);points5[a].append(ap);points10[h].append(hp);points10[a].append(ap);homepoints5[h].append(hp);awaypoints5[a].append(ap);gf5[h].append(float(hg));ga5[h].append(float(ag));gf5[a].append(float(ag));ga5[a].append(float(hg));gd10[h].append(float(hg-ag));gd10[a].append(float(ag-hg))
  expected=1/(1+10**((state[a].elo-(state[h].elo+60))/400));actual=1. if result=="HOME" else .5 if result=="DRAW" else 0.;delta=20*(actual-expected);state[h].elo+=delta;state[a].elo-=delta
 current={normalize_team_name(t):{"name":t,"elo":s.elo,"ppg_5":_avg(points5[t]),"ppg_10":_avg(points10[t]),"home_ppg_5":_avg(homepoints5[t]),"away_ppg_5":_avg(awaypoints5[t]),"gf_5":_avg(gf5[t]),"ga_5":_avg(ga5[t]),"gd_10":_avg(gd10[t],0.),"matches":len(points10[t])} for t,s in state.items()};return np.asarray(x,float),np.asarray(y),meta,current

def brier(y,probs,classes):
 truth=np.zeros_like(probs);lookup={v:i for i,v in enumerate(classes)}
 for i,v in enumerate(y):truth[i,lookup[v]]=1
 return float(np.mean(np.sum((probs-truth)**2,axis=1)))

def _model(c):return Pipeline([("scaler",StandardScaler()),("classifier",LogisticRegression(max_iter=2500,C=c))])

def train_league(key:str,out:Path):
 x,y,meta,states=build_examples(download_rows(key));n=len(y);train_end=int(n*.70);val_end=int(n*.80)
 if train_end<100 or val_end<=train_end or val_end>=n:raise RuntimeError("Not enough completed matches")
 trials=[];best_c=None;best_loss=float("inf")
 for c in C_VALUES:
  candidate=_model(c);candidate.fit(x[:train_end],y[:train_end]);p=candidate.predict_proba(x[train_end:val_end]);classes=candidate.classes_;loss=float(log_loss(y[train_end:val_end],p,labels=classes));acc=float(accuracy_score(y[train_end:val_end],candidate.predict(x[train_end:val_end])));trials.append({"C":c,"validation_log_loss":loss,"validation_accuracy":acc})
  if loss<best_loss:best_loss=loss;best_c=c
 model=_model(best_c);model.fit(x[:val_end],y[:val_end]);probs=model.predict_proba(x[val_end:]);pred=model.predict(x[val_end:]);classes=model.classes_;cfg=LEAGUES[key]
 metrics={"league":cfg["name"],"model_version":f"{key}-logreg-v3","rows_total":n,"train_rows":train_end,"validation_rows":val_end-train_end,"refit_rows":val_end,"test_rows":n-val_end,"selected_C":best_c,"selection_metric":"validation_log_loss","candidate_trials":trials,"test_accuracy":float(accuracy_score(y[val_end:],pred)),"test_log_loss":float(log_loss(y[val_end:],probs,labels=classes)),"test_brier":brier(y[val_end:],probs,classes),"chronological_train_validation_test":True,"features":FEATURE_NAMES,"team_states":len(states),"validation_first_match":meta[train_end],"test_first_match":meta[val_end],"test_last_match":meta[-1],"data_source":"OpenFootball football.json public-domain results","trained_at_utc":datetime.now(timezone.utc).isoformat(timespec="seconds")}
 out.mkdir(parents=True,exist_ok=True);joblib.dump({"model":model,"classes":list(classes),"feature_names":FEATURE_NAMES,"team_states":states,"league_key":key,"league_name":cfg["name"],"model_version":f"{key}-logreg-v3"},out/f"{key}_logreg_v3.joblib");(out/f"{key}_logreg_v3_metrics.json").write_text(json.dumps(metrics,indent=2));return metrics

def train_all(out:Path):
 results={}
 for key in LEAGUES:
  try:results[key]=train_league(key,out)
  except Exception as exc:results[key]={"league":LEAGUES[key]["name"],"error":str(exc)}
 return results
if __name__=="__main__":print(json.dumps(train_all(Path(__file__).resolve().parent/"artifacts"),indent=2))
