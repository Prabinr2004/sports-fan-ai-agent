import httpx
from fastapi import APIRouter,HTTPException,Query
from app.ml.baseline import baseline_probabilities,form_from_matches
from app.ml.europe import predict_cross_league
from app.ml.trained import predict_from_team_names
from app.services.football import get_football_provider
router=APIRouter(prefix="/ml",tags=["ml-predictions"])
@router.get("/predict/{match_id}")
async def predict_match(match_id:str,home_name:str|None=Query(default=None),away_name:str|None=Query(default=None),competition:str|None=Query(default=None))->dict:
 if home_name and away_name:
  trained=predict_from_team_names(home_name,away_name,competition)
  if trained is not None:return {"match_id":match_id,"home_team":home_name,"away_team":away_name,"available":True,**trained,"disclaimer":"FanSphere ML v2 uses a calibrated league-specific model trained on public-domain historical results."}
  cross=predict_cross_league(home_name,away_name,competition)
  if cross is not None:return {"match_id":match_id,"home_team":home_name,"away_team":away_name,"available":True,**cross,"disclaimer":"Cross-league preview uses normalized domestic v2 club strength. It is intentionally conservative until the shared European-results model is trained and validated."}
 provider=get_football_provider()
 try:match=await provider.get_match(match_id)
 except httpx.HTTPStatusError as exc:
  if exc.response.status_code==429:return {"match_id":match_id,"home_team":home_name,"away_team":away_name,"available":False,"reason":"A local model is not available for these teams, and live form data is temporarily rate limited."}
  raise HTTPException(status_code=502,detail="Match data is temporarily unavailable.")
 home=match.get("home_team") or {};away=match.get("away_team") or {};home_id=str(home.get("id"));away_id=str(away.get("id"))
 if not home_id or not away_id or home_id=="None" or away_id=="None":raise HTTPException(status_code=422,detail="Team identifiers are unavailable for this match.")
 try:home_results=await provider.get_recent_results(home_id);away_results=await provider.get_recent_results(away_id)
 except httpx.HTTPStatusError as exc:
  if exc.response.status_code==429:return {"match_id":match_id,"home_team":home.get("name"),"away_team":away.get("name"),"available":False,"reason":"A local model is not available for these teams, and recent-form data is temporarily rate limited."}
  raise HTTPException(status_code=502,detail="Historical match data is temporarily unavailable.")
 result=baseline_probabilities(form_from_matches(home_results,home_id),form_from_matches(away_results,away_id))
 return {"match_id":match_id,"home_team":home.get("name"),"away_team":away.get("name"),"available":True,**result,"disclaimer":"Recent-form fallback; a trained local model is not available for these teams yet."}
