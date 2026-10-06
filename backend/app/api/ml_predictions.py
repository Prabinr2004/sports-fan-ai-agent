import httpx
from fastapi import APIRouter,HTTPException,Query
from app.ml.europe import predict_cross_league,predict_trained_europe
from app.ml.trained import predict_from_team_names
from app.services.football import get_football_provider

router=APIRouter(prefix="/ml",tags=["ml-predictions"])

def _is_european_competition(name:str|None)->bool:
 if not name:return False
 n=name.casefold()
 return any(token in n for token in ("champions league","europa league","conference league","uefa"))

@router.get("/predict/{match_id}")
async def predict_match(match_id:str,home_name:str|None=Query(default=None),away_name:str|None=Query(default=None),competition:str|None=Query(default=None))->dict:
 if home_name and away_name:
  if _is_european_competition(competition):
   european=predict_trained_europe(home_name,away_name)
   if european is not None:
    return {"match_id":match_id,"home_team":home_name,"away_team":away_name,"available":True,**european,"disclaimer":"FanSphere European model is trained on public-domain UEFA competition results with a shared cross-country Elo scale."}
  trained=predict_from_team_names(home_name,away_name,competition)
  if trained is not None:
   return {"match_id":match_id,"home_team":home_name,"away_team":away_name,"available":True,**trained,"disclaimer":"FanSphere ML v2 uses a calibrated league-specific model trained on public-domain historical results."}
  cross=predict_cross_league(home_name,away_name,competition)
  if cross is not None:
   disclaimer="FanSphere European model uses historical European competition results." if cross.get("training_status")=="trained-on-european-results" else "Cross-league preview uses normalized domestic v2 club strength and is intentionally conservative until both clubs are covered by the trained European model."
   return {"match_id":match_id,"home_team":home_name,"away_team":away_name,"available":True,**cross,"disclaimer":disclaimer}

 try:
  provider=get_football_provider();match=await provider.get_match(match_id)
  home=match.get("home_team") or {};away=match.get("away_team") or {}
  resolved_home=home.get("name") or home_name;resolved_away=away.get("name") or away_name
 except (httpx.HTTPStatusError,HTTPException):
  resolved_home=home_name;resolved_away=away_name
 return {"match_id":match_id,"home_team":resolved_home,"away_team":resolved_away,"available":False,"reason":"FanSphere does not have a validated local model for one or both clubs yet. An uncalibrated recent-form percentage is intentionally not shown.","training_status":"unsupported-club-awaiting-european-model"}
