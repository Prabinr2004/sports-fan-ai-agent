import httpx
from fastapi import APIRouter, HTTPException

from app.ml.baseline import baseline_probabilities, form_from_matches
from app.ml.trained import predict_from_recent_results
from app.services.football import get_football_provider

router = APIRouter(prefix="/ml", tags=["ml-predictions"])


@router.get("/predict/{match_id}")
async def predict_match(match_id: str) -> dict:
    provider = get_football_provider()
    try:
        match = await provider.get_match(match_id)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 429:
            raise HTTPException(status_code=429, detail="Match data is temporarily rate limited. Try again after the provider window resets.")
        raise HTTPException(status_code=502, detail="Match data is temporarily unavailable.")

    home = match.get("home_team") or {}
    away = match.get("away_team") or {}
    home_id = str(home.get("id")); away_id = str(away.get("id"))
    if not home_id or not away_id or home_id == "None" or away_id == "None":
        raise HTTPException(status_code=422, detail="Team identifiers are unavailable for this match.")

    home_results: list[dict] = []; away_results: list[dict] = []; unavailable: list[str] = []
    for label, team_id in (("home", home_id), ("away", away_id)):
        try:
            results = await provider.get_recent_results(team_id)
            if label == "home": home_results = results
            else: away_results = results
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 429: unavailable.append(label)
            else: raise HTTPException(status_code=502, detail="Historical match data is temporarily unavailable.")

    if unavailable:
        return {"match_id": match_id, "home_team": home.get("name"), "away_team": away.get("name"), "available": False, "reason": "Recent-form data is temporarily rate limited. Cached form will be used automatically once it has been loaded successfully."}

    # EPL fixtures use the trained model when the locally generated artifact exists.
    competition = (match.get("competition") or "").casefold()
    if "premier league" in competition:
        trained = predict_from_recent_results(home_results, away_results, home_id, away_id)
        if trained is not None:
            return {
                "match_id": match_id,
                "home_team": home.get("name"),
                "away_team": away.get("name"),
                "available": True,
                **trained,
                "disclaimer": "FanSphere ML v1 is trained on historical EPL results. Live Elo is currently estimated from recent form until persistent team Elo state is added.",
            }

    # Keep the transparent baseline for non-EPL matches or machines where the
    # trained artifact has not been generated yet.
    result = baseline_probabilities(form_from_matches(home_results, home_id), form_from_matches(away_results, away_id))
    return {
        "match_id": match_id,
        "home_team": home.get("name"),
        "away_team": away.get("name"),
        "available": True,
        **result,
        "disclaimer": "Recent-form baseline fallback; a trained league model is not available for this match yet.",
    }
