from app.api.auth import require_user
from fastapi import Request, APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.matches import _find_personalized_match
from app.api.ml_predictions import predict_match
from app.core.config import settings
from app.database.session import get_db
from app.models.analysis import MatchAnalysisUnlock
from app.services.analysis_access import analysis_access_summary, unlock_analysis
from app.services.football import get_football_provider
from app.services.openrouter import AIAnalysisUnavailable, explain_match

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.get("/access")
def get_analysis_access(request: Request, match_id: str | None = Query(default=None), db: Session = Depends(get_db)) -> dict:
    user = require_user(request, db)
    existing = db.scalar(select(MatchAnalysisUnlock).where(MatchAnalysisUnlock.user_id == user.id, MatchAnalysisUnlock.match_id == match_id)) if match_id else None
    return {**analysis_access_summary(db, user.id), "match_unlocked": existing is not None, "rich_analysis_available": bool(settings.openrouter_api_key)}


@router.post("/{match_id}/rich")
async def rich_match_analysis(match_id: str, request: Request, db: Session = Depends(get_db)) -> dict:
    user = require_user(request, db)
    if not settings.openrouter_api_key:
        raise HTTPException(status_code=503, detail="Rich FanSphere analysis is not configured.")

    fixture = await _find_personalized_match(db, user, match_id)
    if fixture is None:
        raise HTTPException(status_code=404, detail="This match is not available in your personalized match feed.")

    existing_unlock = db.scalar(select(MatchAnalysisUnlock).where(
        MatchAnalysisUnlock.user_id == user.id,
        MatchAnalysisUnlock.match_id == match_id,
    ))
    access = analysis_access_summary(db, user.id)
    if existing_unlock is not None and existing_unlock.analysis_text:
        return {
            "analysis": existing_unlock.analysis_text,
            "access": {"unlocked": True, "source": existing_unlock.unlock_source, "charged": False, **access},
            "cached": True,
        }
    if existing_unlock is None and access["free_remaining"] == 0 and (access["extra_remaining"] <= 0 or access["gems"] < access["gems_per_analysis"]):
        raise HTTPException(status_code=402, detail="No free match analysis remains today. Exchange XP for Gems in Wallet to unlock another match.")

    home = fixture.get("home_team") or {}
    away = fixture.get("away_team") or {}
    competition = fixture.get("competition") or {}

    provider = get_football_provider()

    async def recent_summary(team: dict) -> dict:
        team_id = str(team.get("id") or "")
        if not team_id:
            return {"matches": 0}
        try:
            results = await provider.get_recent_results(team_id, limit=5)
        except Exception:
            return {"matches": 0}

        wins = draws = losses = goals_for = goals_against = 0
        for result in results:
            result_home = result.get("home_team") or {}
            score = result.get("score") or {}
            home_score, away_score = score.get("home"), score.get("away")
            if home_score is None or away_score is None:
                continue
            is_home = str(result_home.get("id")) == team_id
            gf, ga = (home_score, away_score) if is_home else (away_score, home_score)
            goals_for += gf
            goals_against += ga
            if gf > ga:
                wins += 1
            elif gf == ga:
                draws += 1
            else:
                losses += 1
        return {"matches": wins + draws + losses, "wins": wins, "draws": draws, "losses": losses, "goals_for": goals_for, "goals_against": goals_against}

    comparison = {"home_recent": await recent_summary(home), "away_recent": await recent_summary(away)}
    model_outlook = await predict_match(
        match_id,
        home_name=home.get("name"),
        away_name=away.get("name"),
        competition=competition.get("name"),
    )
    if model_outlook.get("available") is False:
        model_outlook = None

    try:
        explanation = await explain_match(
            home_team=home.get("name") or "Home team",
            away_team=away.get("name") or "Away team",
            competition=competition.get("name"),
            model_outlook=model_outlook,
            comparison=comparison,
        )
    except AIAnalysisUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    unlocked = unlock_analysis(db, user.id, match_id, explanation)
    if not unlocked["unlocked"]:
        raise HTTPException(status_code=402, detail=unlocked["reason"])
    return {"analysis": explanation, "access": unlocked, "cached": False}
