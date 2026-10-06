import httpx
from fastapi import APIRouter, HTTPException, Query

from app.ml.baseline import baseline_probabilities, form_from_matches
from app.ml.trained import predict_from_team_names
from app.services.football import get_football_provider

router = APIRouter(prefix="/ml", tags=["ml-predictions"])

@router.get("/predict/{match_id}")
async def predict_match(match_id:str, home_name:str|None=Query(default=None), away_name:str|None=Query(default=None))->dict:
    # Fast path: EPL teams stored in the trained artifact need zero football-provider
    # requests. This avoids spending the free API quota just to analyze a fixture.
    if home_name and away_name:
        trained=predict_from_team_names(home_name,away_name)
        if trained is not None:
            return {"match_id":match_id,"home_team":home_name,"away_team":away_name,"available":True,**trained,"disclaimer":"FanSphere ML v1 · trained on historical EPL results through the latest downloaded dataset."}

    provider=get_football_provider()
    try: match=await provider.get_match(match_id)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code==429: raise HTTPException(status_code=429,detail="Match data is temporarily rate limited. Try again after the provider window resets.")
        raise HTTPException(status_code=502,detail="Match data is temporarily unavailable.")
    home=match.get("home_team") or {}; away=match.get("away_team") or {}; home_id=str(home.get("id")); away_id=str(away.get("id"))
    if not home_id or not away_id or home_id=="None" or away_id=="None": raise HTTPException(status_code=422,detail="Team identifiers are unavailable for this match.")
    home_results=[]; away_results=[]; unavailable=[]
    for label,team_id in (("home",home_id),("away",away_id)):
        try:
            results=await provider.get_recent_results(team_id)
            if label=="home":home_results=results
            else:away_results=results
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code==429:unavailable.append(label)
            else:raise HTTPException(status_code=502,detail="Historical match data is temporarily unavailable.")
    if unavailable:return {"match_id":match_id,"home_team":home.get("name"),"away_team":away.get("name"),"available":False,"reason":"Recent-form data is temporarily rate limited. This match does not have a local trained-league state yet."}
    result=baseline_probabilities(form_from_matches(home_results,home_id),form_from_matches(away_results,away_id))
    return {"match_id":match_id,"home_team":home.get("name"),"away_team":away.get("name"),"available":True,**result,"disclaimer":"Recent-form baseline fallback; a trained league model is not available for this match yet."}
