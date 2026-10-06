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

FEATURE_NAMES=["home_ppg_5","away_ppg_5","home_gf_5","away_gf_5","home_ga_5","away_ga_5","home_elo","away_elo","elo_diff"]
SEASONS=("2022-23","2023-24","2024-25","2025-26","2026-27")
LEAGUES={"epl":{"name":"Premier League","file":"en.1.json"},"laliga":{"name":"La Liga","file":"es.1.json"},"bundesliga":{"name":"Bundesliga","file":"de.1.json"},"seriea":{"name":"Serie A","file":"it.1.json"},"ligue1":{"name":"Ligue 1","file":"fr.1.json"}}
DATA_URL="https://raw.githubusercontent.com/openfootball/football.json/master/{season}/{file}"
@dataclass
class TeamState:elo:float=1500.
def normalize_team_name(name:str)->str:
 s=unicodedata.normalize("NFKD",name).encode("ascii","ignore").decode().casefold();s=re.sub(r"\b(fc|cf|afc|calcio|football club|futbol club|club de futbol)\b"," ",s);return re.sub(r"[^a-z0-9]+","",s)
def _avg(v,default=1.35):return sum(v)/len(v) if v else default

def download_rows(key:str)->list[dict[str,Any]]:
 cfg=LEAGUES[key];rows=[]
 with httpx.Client(timeout=30.,follow_redirects=True,headers={"User-Agent":"FanSphere-ML/2.0"}) as client:
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
 state=defaultdict(TeamState);points=defaultdict(lambda:deque(maxlen=5));gf=defaultdict(lambda:deque(maxlen=5));ga=defaultdict(lambda:deque(maxlen=5));x=[];y=[];meta=[]
 for r in rows:
  h,a,hg,ag=r["home"],r["away"],r["hg"],r["ag"]
  if len(points[h])>=3 and len(points[a])>=3:
   he,ae=state[h].elo,state[a].elo;x.append([_avg(points[h]),_avg(points[a]),_avg(gf[h]),_avg(gf[a]),_avg(ga[h]),_avg(ga[a]),he,ae,he-ae]);y.append("HOME" if hg>ag else "AWAY" if ag>hg else "DRAW");meta.append({"date":r["date"],"season":r["season"],"home":h,"away":a})
  result="HOME" if hg>ag else "AWAY" if ag>hg else "DRAW";hp,ap=(3.,0.) if result=="HOME" else ((1.,1.) if result=="DRAW" else (0.,3.));points[h].append(hp);points[a].append(ap);gf[h].append(float(hg));ga[h].append(float(ag));gf[a].append(float(ag));ga[a].append(float(hg));expected=1/(1+10**((state[a].elo-(state[h].elo+60))/400));actual=1. if result=="HOME" else .5 if result=="DRAW" else 0.;delta=20*(actual-expected);state[h].elo+=delta;state[a].elo-=delta
 current={normalize_team_name(t):{"name":t,"elo":s.elo,"ppg_5":_avg(points[t]),"gf_5":_avg(gf[t]),"ga_5":_avg(ga[t]),"matches":len(points[t])} for t,s in state.items()};return np.asarray(x,float),np.asarray(y),meta,current

def brier(y,probs,classes):
 truth=np.zeros_like(probs);lookup={v:i for i,v in enumerate(classes)}
 for i,v in enumerate(y):truth[i,lookup[v]]=1
 return float(np.mean(np.sum((probs-truth)**2,axis=1)))

def train_league(key:str,out:Path):
 x,y,meta,states=build_examples(download_rows(key));split=int(len(y)*.8)
 if split<100:raise RuntimeError("Not enough completed matches")
 model=Pipeline([("scaler",StandardScaler()),("classifier",LogisticRegression(max_iter=1500,C=.35,class_weight="balanced"))]);model.fit(x[:split],y[:split]);probs=model.predict_proba(x[split:]);pred=model.predict(x[split:]);classes=model.named_steps["classifier"].classes_;cfg=LEAGUES[key]
 metrics={"league":cfg["name"],"model_version":f"{key}-logreg-v1","rows_total":len(y),"train_rows":split,"test_rows":len(y)-split,"test_accuracy":float(accuracy_score(y[split:],pred)),"test_log_loss":float(log_loss(y[split:],probs,labels=classes)),"test_brier":brier(y[split:],probs,classes),"chronological_split":True,"team_states":len(states),"test_first_match":meta[split],"test_last_match":meta[-1],"data_source":"OpenFootball football.json public-domain results","trained_at_utc":datetime.now(timezone.utc).isoformat(timespec="seconds")}
 out.mkdir(parents=True,exist_ok=True);joblib.dump({"model":model,"classes":list(classes),"feature_names":FEATURE_NAMES,"team_states":states,"league_key":key,"league_name":cfg["name"]},out/f"{key}_logreg_v1.joblib");(out/f"{key}_logreg_v1_metrics.json").write_text(json.dumps(metrics,indent=2));return metrics

def train_all(out:Path):
 results={}
 for key in LEAGUES:
  try:results[key]=train_league(key,out)
  except Exception as exc:results[key]={"league":LEAGUES[key]["name"],"error":str(exc)}
 return results
if __name__=="__main__":print(json.dumps(train_all(Path(__file__).resolve().parent/"artifacts"),indent=2))
