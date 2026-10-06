from __future__ import annotations

import json
import re
import unicodedata
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, log_loss
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

SEASONS=("2019-20","2020-21","2021-22","2022-23","2023-24","2024-25","2025-26")
FILES=("cl.txt","el.txt","conf.txt","clq.txt","elq.txt","confq.txt")
BASE_URL="https://raw.githubusercontent.com/openfootball/champions-league/master/{season}/{file}"
FEATURE_NAMES=["home_ppg_5","away_ppg_5","home_ppg_10","away_ppg_10","home_gf_5","away_gf_5","home_ga_5","away_ga_5","home_gd_10","away_gd_10","home_elo","away_elo","elo_diff"]
MATCH_RE=re.compile(r"^(?:\d{1,2}:\d{2}\s+)?(.+?)\s+\(([A-Z]{3})\)\s+v\s+(.+?)\s+\(([A-Z]{3})\)\s+(\d+)-(\d+)(?:\s|$)")
DATE_RE=re.compile(r"^(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+([A-Z][a-z]{2})\s+(\d{1,2})(?:\s+(\d{4}))?$")
MONTHS={m:i for i,m in enumerate(("Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"),1)}

@dataclass
class TeamState:
    elo:float=1500.0

def normalize_team_name(name:str)->str:
 s=unicodedata.normalize("NFKD",name).encode("ascii","ignore").decode().casefold()
 s=re.sub(r"\b(fc|cf|afc|sk|fk|ac|as|ssc|ss|club|football club|futbol club|club de futbol)\b"," ",s)
 return re.sub(r"[^a-z0-9]+","",s)

def _avg(values,default=1.35):return sum(values)/len(values) if values else default

def _season_year(season:str,month:int)->int:
 start=int(season[:4]);return start if month>=7 else start+1

def _parse_text(text:str,season:str,source_file:str)->list[dict[str,Any]]:
 rows=[];current_date=None
 for raw in text.splitlines():
  line=raw.strip()
  if not line:continue
  dm=DATE_RE.match(line)
  if dm:
   mon,day,year=dm.groups();month=MONTHS[mon]
   current_date=datetime(int(year) if year else _season_year(season,month),month,int(day))
   continue
  if " pen." in line or "a.e.t." in line:continue
  match=MATCH_RE.match(line)
  if not match or current_date is None:continue
  home,hc,away,ac,hg,ag=match.groups()
  rows.append({"home":home.strip(),"away":away.strip(),"home_country":hc,"away_country":ac,"hg":int(hg),"ag":int(ag),"season":season,"source_file":source_file,"date":current_date})
 return rows

def download_rows()->list[dict[str,Any]]:
 rows=[]
 with httpx.Client(timeout=30.,follow_redirects=True,headers={"User-Agent":"FanSphere-European-ML/2.0"}) as client:
  for season in SEASONS:
   total=0
   for filename in FILES:
    response=client.get(BASE_URL.format(season=season,file=filename))
    if response.status_code==404:continue
    response.raise_for_status();parsed=_parse_text(response.text,season,filename);rows.extend(parsed);total+=len(parsed)
   print(f"Europe {season}: {total} dated usable matches")
 rows.sort(key=lambda r:(r["date"],r["source_file"],r["home"],r["away"]))
 return rows

def build_examples(rows):
 state=defaultdict(TeamState);points5=defaultdict(lambda:deque(maxlen=5));points10=defaultdict(lambda:deque(maxlen=10));gf5=defaultdict(lambda:deque(maxlen=5));ga5=defaultdict(lambda:deque(maxlen=5));gd10=defaultdict(lambda:deque(maxlen=10));country={};display={};x=[];y=[];meta=[]
 for r in rows:
  h=normalize_team_name(r["home"]);a=normalize_team_name(r["away"])
  if not h or not a or h==a:continue
  country[h]=r["home_country"];country[a]=r["away_country"];display[h]=r["home"];display[a]=r["away"];hg,ag=r["hg"],r["ag"]
  if len(points5[h])>=2 and len(points5[a])>=2:
   he,ae=state[h].elo,state[a].elo
   x.append([_avg(points5[h]),_avg(points5[a]),_avg(points10[h]),_avg(points10[a]),_avg(gf5[h]),_avg(gf5[a]),_avg(ga5[h]),_avg(ga5[a]),_avg(gd10[h],0.),_avg(gd10[a],0.),he,ae,he-ae])
   result="HOME" if hg>ag else "AWAY" if ag>hg else "DRAW";y.append(result);meta.append({"date":r["date"].date().isoformat(),"season":r["season"],"home":r["home"],"away":r["away"],"competition_file":r["source_file"]})
  result="HOME" if hg>ag else "AWAY" if ag>hg else "DRAW";hp,ap=(3.,0.) if result=="HOME" else ((1.,1.) if result=="DRAW" else (0.,3.))
  points5[h].append(hp);points5[a].append(ap);points10[h].append(hp);points10[a].append(ap);gf5[h].append(float(hg));ga5[h].append(float(ag));gf5[a].append(float(ag));ga5[a].append(float(hg));gd10[h].append(float(hg-ag));gd10[a].append(float(ag-hg))
  expected=1./(1.+10**((state[a].elo-(state[h].elo+45.))/400.));actual=1. if result=="HOME" else .5 if result=="DRAW" else 0.;delta=24.*(actual-expected);state[h].elo+=delta;state[a].elo-=delta
 team_states={k:{"name":display.get(k,k),"country":country.get(k),"elo":st.elo,"ppg_5":_avg(points5[k]),"ppg_10":_avg(points10[k]),"gf_5":_avg(gf5[k]),"ga_5":_avg(ga5[k]),"gd_10":_avg(gd10[k],0.),"matches":len(points10[k])} for k,st in state.items()}
 return np.asarray(x,float),np.asarray(y),meta,team_states

def brier(y_true,probs,classes):
 truth=np.zeros_like(probs);lookup={v:i for i,v in enumerate(classes)}
 for i,v in enumerate(y_true):truth[i,lookup[v]]=1.
 return float(np.mean(np.sum((probs-truth)**2,axis=1)))

def train_europe(out:Path):
 x,y,meta,states=build_examples(download_rows())
 if len(y)<500:raise RuntimeError(f"Not enough European training rows: {len(y)}")
 split=int(len(y)*.8)
 model=Pipeline([("scaler",StandardScaler()),("classifier",LogisticRegression(max_iter=2500,C=.25))]);model.fit(x[:split],y[:split]);probs=model.predict_proba(x[split:]);pred=model.predict(x[split:]);classes=model.named_steps["classifier"].classes_
 metrics={"model_version":"europe-logreg-v2","rows_total":len(y),"train_rows":split,"test_rows":len(y)-split,"test_accuracy":float(accuracy_score(y[split:],pred)),"test_log_loss":float(log_loss(y[split:],probs,labels=classes)),"test_brier":brier(y[split:],probs,classes),"chronological_order":True,"features":FEATURE_NAMES,"team_states":len(states),"test_first_match":meta[split],"test_last_match":meta[-1],"data_source":"OpenFootball champions-league CC0/public-domain European competition results","trained_at_utc":datetime.now(timezone.utc).isoformat(timespec="seconds")}
 out.mkdir(parents=True,exist_ok=True);joblib.dump({"model":model,"classes":list(classes),"feature_names":FEATURE_NAMES,"team_states":states,"model_version":"europe-logreg-v2"},out/"europe_logreg_v2.joblib");(out/"europe_logreg_v2_metrics.json").write_text(json.dumps(metrics,indent=2));return metrics

if __name__=="__main__":
 artifact_dir=Path(__file__).resolve().parent/"artifacts";print(json.dumps(train_europe(artifact_dir),indent=2))
