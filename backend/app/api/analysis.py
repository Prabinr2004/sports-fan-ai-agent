from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.matches import _find_personalized_match
from app.api.profile import _get_or_create_local_user
from app.core.config import settings
from app.database.session import get_db
from app.models.analysis import MatchAnalysisUnlock
from app.services.analysis_access import analysis_access_summary, unlock_analysis
from app.services.football import get_football_provider
from app.services.openrouter import AIAnalysisUnavailable, explain_match

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.get("/access")
def get_analysis_access(db: Session = Depends(get_db)) -> dict:
    user = _get_or_create_local_user(db)
    return {**analysis_access_summary(db, user.id), "rich_analysis_available": bool(settings.openrouter_api_key)}


@router.post("/{match_id}/rich")
async def rich_match_analysis(match_id: str, db: Session = Depends(get_db)) -> dict:
    user = _get_or_create_local_user(db)
    if not settings.openrouter_api_key:
        raise HTTPException(status_code=503, detail="Rich FanSphere analysis is not configured.")

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
    if existing_unlock is None and access["free_remaining"] == 0 and access["tokens"] <= 0:
        raise HTTPException(status_code=402, detail="Complete today's rewarded Daily Quiz to earn an Analysis Token.")

    fixture = await _find_personalized_match(db, user, match_id)
    if fixture is None:
        raise HTTPException(status_code=404, detail="This match is not available in your personalized match feed.")

    home = fixture.get("home_team") or {}
    away = fixture.get("away_team") or {}
    competition = fixture.get("competition") or {}

    try:
        explanation = await explain_match(
            home_team=home.get("name") or "Home team",
            away_team=away.get("name") or "Away team",
            competition=competition.get("name"),
            model_outlook=None,
            comparison=comparison,
        )
    except AIAnalysisUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    unlocked = unlock_analysis(db, user.id, match_id, explanation)
    if not unlocked["unlocked"]:
        raise HTTPException(status_code=402, detail=unlocked["reason"])
    return {"analysis": explanation, "access": unlocked, "cached": False}
