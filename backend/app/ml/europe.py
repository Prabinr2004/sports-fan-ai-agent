from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any
import math
import re
import unicodedata

import joblib
import numpy as np

from app.ml.trained import SUPPORTED, load_model_bundle, _find

ARTIFACT_DIR = Path(__file__).resolve().parent / "artifacts"
LEAGUE_OFFSETS={"epl":20.0,"laliga":15.0,"bundesliga":10.0,"seriea":10.0,"ligue1":0.0}

def _key(name:str)->str:
 s=unicodedata.normalize("NFKD",name).encode("ascii","ignore").decode().casefold()
 s=re.sub(r"\b(fc|cf|afc|sk|fk|ac|as|ssc|ss|club|football club|futbol club|club de futbol)\b"," ",s)
 return re.sub(r"[^a-z0-9]+","",s)

EUROPE_ALIASES={
 "intermilan":"internazionalemilano",
 "inter":"internazionalemilano",
 "bayernmunich":"bayernmunchen",
 "bayern":"bayernmunchen",
 "psg":"parissaintgermain",
 "parissg":"parissaintgermain",
 "atleticomadrid":"atleticodemadrid",
 "sportinglisbon":"sportingclubedeportugal",
 "benfica":"sportlisboaebenfica",
 "olympiacos":"paeolympiakossfp",
 "olympiakos":"paeolympiakossfp",
}

@lru_cache(maxsize=1)
def load_europe_bundle()->dict[str,Any]|None:
 path=ARTIFACT_DIR/"europe_logreg_v1.joblib"
 return joblib.load(path) if path.exists() else None

def _find_europe(states:dict[str,Any],name:str):
 wanted=_key(name)
 if wanted in states:return states[wanted]
 target=EUROPE_ALIASES.get(wanted,wanted)
 for k,v in states.items():
  if EUROPE_ALIASES.get(k,k)==target:return v
 return None

def _feature_row(home:dict[str,Any],away:dict[str,Any],names:list[str])->np.ndarray:
 values={
  "home_ppg_5":home.get("ppg_5",1.35),
  "away_ppg_5":away.get("ppg_5",1.35),
  "home_ppg_10":home.get("ppg_10",home.get("ppg_5",1.35)),
  "away_ppg_10":away.get("ppg_10",away.get("ppg_5",1.35)),
  "home_gf_5":home.get("gf_5",1.35),
  "away_gf_5":away.get("gf_5",1.35),
  "home_ga_5":home.get("ga_5",1.35),
  "away_ga_5":away.get("ga_5",1.35),
  "home_gd_10":home.get("gd_10",0.0),
  "away_gd_10":away.get("gd_10",0.0),
  "home_elo":home["elo"],
  "away_elo":away["elo"],
  "elo_diff":home["elo"]-away["elo"],
  "home_advantage":1.0,
 }
 return np.asarray([[values[n] for n in names]],float)

def predict_trained_europe(home_name:str,away_name:str)->dict[str,Any]|None:
 bundle=load_europe_bundle()
 if bundle is None:return None
 states=bundle.get("team_states") or {}
 home=_find_europe(states,home_name);away=_find_europe(states,away_name)
 if home is None or away is None:return None
 model=bundle["model"];names=bundle.get("feature_names") or []
 p=model.predict_proba(_feature_row(home,away,names))[0]
 classes=list(getattr(model,"classes_",bundle.get("classes",[])))
 probs={str(c):float(p[i]) for i,c in enumerate(classes)}
 return {
  "probabilities":{"HOME":probs.get("HOME",0.),"DRAW":probs.get("DRAW",0.),"AWAY":probs.get("AWAY",0.)},
  "pick":max(probs,key=probs.get),
  "model_version":bundle.get("model_version","europe-logreg-v1"),
  "league_model":"Shared European competition model",
  "model_type":"scaled-multinomial-logistic-regression",
  "training_status":"trained-on-european-results",
  "feature_state":"shared-european-elo-and-form",
  "strength":{"home_elo":round(float(home["elo"]),1),"away_elo":round(float(away["elo"]),1),"home_country":home.get("country"),"away_country":away.get("country")},
 }

@lru_cache(maxsize=1)
def _clubs()->dict[str,list[tuple[str,dict[str,Any]]]]:
 out={}
 for league in SUPPORTED:
  bundle=load_model_bundle(league)
  if bundle:out[league]=list((bundle.get("team_states") or {}).items())
 return out

def _lookup_domestic(name:str):
 for league in SUPPORTED:
  bundle=load_model_bundle(league)
  if not bundle:continue
  state=_find(bundle.get("team_states") or {},name)
  if state is not None:return league,state
 return None,None

def _league_elo_stats(league:str)->tuple[float,float]:
 rows=_clubs().get(league,[]);vals=[float(v["elo"]) for _,v in rows]
 if not vals:return 1500.,100.
 mean=sum(vals)/len(vals);sd=math.sqrt(sum((v-mean)**2 for v in vals)/max(1,len(vals)-1))
 return mean,max(sd,45.)

def _shared_strength(league:str,state:dict[str,Any])->float:
 mean,sd=_league_elo_stats(league);z=(float(state["elo"])-mean)/sd
 form=(float(state.get("ppg_10",state.get("ppg_5",1.35)))-1.35)*45.
 gd=float(state.get("gd_10",0.))*18.
 return 1500.+z*95.+form+gd+LEAGUE_OFFSETS.get(league,0.)

def _softmax(values:list[float])->list[float]:
 m=max(values);e=[math.exp(v-m) for v in values];s=sum(e);return [v/s for v in e]

def predict_cross_league(home_name:str,away_name:str,competition:str|None=None)->dict[str,Any]|None:
 trained=predict_trained_europe(home_name,away_name)
 if trained is not None:return trained
 hl,home=_lookup_domestic(home_name);al,away=_lookup_domestic(away_name)
 if home is None or away is None or hl==al:return None
 hs=_shared_strength(hl,home);as_=_shared_strength(al,away);diff=hs-as_
 draw_logit=0.15-abs(diff)/260.
 home_logit=(diff+45.)/170.
 away_logit=(-diff)/170.
 p=_softmax([home_logit,draw_logit,away_logit]);probs={"HOME":p[0],"DRAW":p[1],"AWAY":p[2]}
 return {"probabilities":probs,"pick":max(probs,key=probs.get),"model_version":"europe-strength-bridge-v1","league_model":"Cross-league European strength","model_type":"cross-league-strength-bridge","training_status":"bridge-not-yet-trained-on-european-results","feature_state":"domestic-v2-strength-normalized-across-leagues","strength":{"home":round(hs,1),"away":round(as_,1),"home_league":hl,"away_league":al}}
