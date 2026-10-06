from __future__ import annotations
from functools import lru_cache
from pathlib import Path
from typing import Any
import re,unicodedata,joblib,numpy as np
ARTIFACT_DIR=Path(__file__).resolve().parent/"artifacts";SUPPORTED=("epl","laliga","bundesliga","seriea","ligue1")
# Experimental artifacts (v3+) are intentionally not auto-promoted. Production
# stays on the explicitly selected version until held-out evaluation justifies a change.
PRODUCTION_MODEL_VERSION={"epl":"v2","laliga":"v2","bundesliga":"v2","seriea":"v2","ligue1":"v2"}
LEAGUE_ALIASES={"premier league":"epl","epl":"epl","primera division":"laliga","la liga":"laliga","laliga":"laliga","bundesliga":"bundesliga","serie a":"seriea","ligue 1":"ligue1"}
def league_key(name:str|None)->str|None:
 if not name:return None
 n=re.sub(r"[^a-z0-9]+"," ",name.casefold()).strip()
 for alias,key in LEAGUE_ALIASES.items():
  if alias in n:return key
 return None
@lru_cache(maxsize=10)
def load_model_bundle(key:str)->dict[str,Any]|None:
 selected=PRODUCTION_MODEL_VERSION.get(key,"v2")
 # Prefer the explicitly approved production artifact. Older versions are only
 # compatibility fallbacks; newer experimental files never silently replace it.
 for version in (selected,"v1"):
  path=ARTIFACT_DIR/f"{key}_logreg_{version}.joblib"
  if path.exists():return joblib.load(path)
 return None
def _key(name:str)->str:
 s=unicodedata.normalize("NFKD",name).encode("ascii","ignore").decode().casefold();s=re.sub(r"\b(fc|cf|afc|calcio|football club|futbol club|club de futbol)\b"," ",s);return re.sub(r"[^a-z0-9]+","",s)
def _find(states,name):
 wanted=_key(name)
 if wanted in states:return states[wanted]
 aliases={"atleticomadrid":"clubatleticodemadrid","athleticbilbao":"athleticclub","betis":"realbetisbalompie","deportivo":"rcdeportivolacoruna","espanyolbarcelona":"rcdespanyoldebarcelona","racingsantander":"realracingclubdesantander","realsociedadsansebastian":"realsociedaddefutbol","celtavigo":"rcceltadevigo","manchestercity":"mancity","manchesterunited":"manutd","tottenhamhotspur":"tottenham","wolverhamptonwanderers":"wolves","brightonhovealbion":"brighton"};target=aliases.get(wanted,wanted)
 for k,v in states.items():
  if aliases.get(k,k)==target:return v
 return None
def _features(home,away,names):
 values={"home_ppg_5":home["ppg_5"],"away_ppg_5":away["ppg_5"],"home_ppg_10":home.get("ppg_10",home["ppg_5"]),"away_ppg_10":away.get("ppg_10",away["ppg_5"]),"home_venue_ppg_5":home.get("home_ppg_5",home["ppg_5"]),"away_venue_ppg_5":away.get("away_ppg_5",away["ppg_5"]),"home_gf_5":home["gf_5"],"away_gf_5":away["gf_5"],"home_ga_5":home["ga_5"],"away_ga_5":away["ga_5"],"home_gd_10":home.get("gd_10",home["gf_5"]-home["ga_5"]),"away_gd_10":away.get("gd_10",away["gf_5"]-away["ga_5"]),"home_elo":home["elo"],"away_elo":away["elo"],"elo_diff":home["elo"]-away["elo"],"home_advantage":1.}
 return np.asarray([[values[n] for n in names]],float)
def predict_from_team_names(home_name:str,away_name:str,competition:str|None=None)->dict[str,Any]|None:
 preferred=league_key(competition);keys=[preferred] if preferred else list(SUPPORTED)
 for key in keys:
  if not key:continue
  bundle=load_model_bundle(key)
  if bundle is None:continue
  states=bundle.get("team_states") or bundle.get("current_team_features") or {};home=_find(states,home_name);away=_find(states,away_name)
  if home is None or away is None:continue
  names=bundle.get("feature_names") or ["home_ppg_5","away_ppg_5","home_gf_5","away_gf_5","home_ga_5","away_ga_5","home_elo","away_elo","elo_diff"]
  features=_features(home,away,names);model=bundle["model"];p=model.predict_proba(features)[0];classes=list(getattr(model,"classes_",bundle.get("classes",[])));probs={str(c):float(p[i]) for i,c in enumerate(classes)};pick=max(probs,key=probs.get);version=bundle.get("model_version",f"{key}-logreg-v1")
  model_type="chronologically-selected-logistic-regression" if version.endswith("v3") else "calibrated-logistic-regression" if version.endswith("v2") else "scaled-multinomial-logistic-regression"
  return {"probabilities":{"HOME":probs.get("HOME",0.),"DRAW":probs.get("DRAW",0.),"AWAY":probs.get("AWAY",0.)},"pick":pick,"model_version":version,"league_model":bundle.get("league_name",key),"model_type":model_type,"training_status":"trained","feature_state":"historical-through-latest-dataset"}
 return None
