import httpx
from fastapi import APIRouter, HTTPException

from app.ml.baseline import baseline_probabilities, form_from_matches
from app.services.football import get_football_provider

router = APIRouter(prefix="/ml", tags=["ml-predictions"])


@router.get("/predict/{match_id}")
async def predict_match(match_id: str) -> dict:
    provider = get_football_provider()
    try:
        match = await provider.get_match(match_id)
        home = match.get("home_team") or {}
        away = match.get("away_team") or {}
        home_id = str(home.get("id"))
        away_id = str(away.get("id"))
        if not home_id or not away_id or home_id == "None" or away_id == "None":
            raise HTTPException(status_code=422, detail="Team identifiers are unavailable for this match.")
        home_results = await provider.get_recent_results(home_id)
        away_results = await provider.get_recent_results(away_id)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 429:
            raise HTTPException(status_code=429, detail="Football provider rate limit reached. Try the model again shortly.")
        raise HTTPException(status_code=502, detail="Historical match data is unavailable for this prediction.")
    result = baseline_probabilities(
        form_from_matches(home_results, home_id),
        form_from_matches(away_results, away_id),
    )
    return {
        "match_id": match_id,
        "home_team": home.get("name"),
        "away_team": away.get("name"),
        **result,
        "disclaimer": "This is a non-monetary fan prediction baseline. It is not a trained ML model yet.",
    }
