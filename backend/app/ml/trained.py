from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any
import re

import joblib
import numpy as np

ARTIFACT = Path(__file__).resolve().parent / "artifacts" / "epl_logreg_v1.joblib"

@lru_cache(maxsize=1)
def load_model_bundle() -> dict[str, Any] | None:
    if not ARTIFACT.exists(): return None
    return joblib.load(ARTIFACT)

def _key(name:str)->str:
    value=name.casefold().replace("manchester","man").replace("united","utd")
    value=re.sub(r"\b(fc|afc|football club)\b","",value)
    return re.sub(r"[^a-z0-9]+","",value)

def _find_team(states:dict[str,dict[str,float]], name:str)->dict[str,float]|None:
    wanted=_key(name)
    for stored,data in states.items():
        if _key(stored)==wanted:return data
    aliases={"manutd":"manunited","mancity":"mancity","nottinghamforest":"nottmforest","tottenhamhotspur":"tottenham","wolverhamptonwanderers":"wolves","brightonhovealbion":"brighton","westhamutd":"westham","newcastleutd":"newcastle","leedsutd":"leeds"}
    target=aliases.get(wanted,wanted)
    for stored,data in states.items():
        if aliases.get(_key(stored),_key(stored))==target:return data
    return None

def predict_from_team_names(home_name:str,away_name:str)->dict[str,Any]|None:
    bundle=load_model_bundle()
    if bundle is None:return None
    states=bundle.get("current_team_features") or {}
    home=_find_team(states,home_name); away=_find_team(states,away_name)
    if home is None or away is None:return None
    features=np.asarray([[home["ppg_5"],away["ppg_5"],home["gf_5"],away["gf_5"],home["ga_5"],away["ga_5"],home["elo"],away["elo"],home["elo"]-away["elo"]]],dtype=float)
    model=bundle["model"]; probabilities=model.predict_proba(features)[0]; classes=list(getattr(model,"classes_",bundle.get("classes",[]))); probs={str(label):float(probabilities[i]) for i,label in enumerate(classes)}; pick=max(probs,key=probs.get)
    return {"probabilities":{"HOME":probs.get("HOME",0.),"DRAW":probs.get("DRAW",0.),"AWAY":probs.get("AWAY",0.)},"pick":pick,"model_version":"epl-logreg-v1","model_type":"scaled-multinomial-logistic-regression","training_status":"trained","feature_state":"historical-through-latest-dataset","features":{"home_ppg_5":home["ppg_5"],"away_ppg_5":away["ppg_5"],"home_gf_5":home["gf_5"],"away_gf_5":away["gf_5"],"home_ga_5":home["ga_5"],"away_ga_5":away["ga_5"],"home_elo":home["elo"],"away_elo":away["elo"],"elo_diff":home["elo"]-away["elo"]}}
