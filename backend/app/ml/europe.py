from __future__ import annotations

from functools import lru_cache
from typing import Any
import math

from app.ml.trained import SUPPORTED, load_model_bundle, _find

# League offsets are intentionally zero-centred. The shared score is driven by
# each club's percentile-like Elo deviation and form, not raw Elo across leagues.
# European competition results will replace this bridge with a trained shared Elo.
LEAGUE_OFFSETS={"epl":20.0,"laliga":15.0,"bundesliga":10.0,"seriea":10.0,"ligue1":0.0}

@lru_cache(maxsize=1)
def _clubs()->dict[str,list[tuple[str,dict[str,Any]]]]:
 out={}
 for league in SUPPORTED:
  bundle=load_model_bundle(league)
  if bundle:
   out[league]=list((bundle.get("team_states") or {}).items())
 return out

def _lookup(name:str):
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
 hl,home=_lookup(home_name);al,away=_lookup(away_name)
 if home is None or away is None or hl==al:return None
 hs=_shared_strength(hl,home);as_=_shared_strength(al,away);diff=hs-as_
 # Conservative three-way bridge. It deliberately avoids extreme confidence
 # until a shared European-results model is trained and evaluated.
 draw_logit=0.15-abs(diff)/260.
 home_logit=(diff+45.)/170.
 away_logit=(-diff)/170.
 p=_softmax([home_logit,draw_logit,away_logit]);probs={"HOME":p[0],"DRAW":p[1],"AWAY":p[2]}
 return {"probabilities":probs,"pick":max(probs,key=probs.get),"model_version":"europe-strength-bridge-v1","league_model":"Cross-league European strength","model_type":"cross-league-strength-bridge","training_status":"bridge-not-yet-trained-on-european-results","feature_state":"domestic-v2-strength-normalized-across-leagues","strength":{"home":round(hs,1),"away":round(as_,1),"home_league":hl,"away_league":al}}
