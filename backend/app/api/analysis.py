import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.profile import _get_or_create_local_user
from app.core.config import settings
from app.database.session import get_db
from app.services.analysis_access import analysis_access_summary, unlock_analysis
from app.services.openrouter import AIAnalysisUnavailable, explain_match

router = APIRouter(prefix="/analysis", tags=["analysis"])


class RichAnalysisRequest(BaseModel):
    home_team: str
    away_team: str
    competition: str | None = None
    model_outlook: dict | None = None
    comparison: dict | None = None


@router.get("/access")
def get_analysis_access(db: Session = Depends(get_db)) -> dict:
    user = _get_or_create_local_user(db)
    return {**analysis_access_summary(db, user.id), "rich_analysis_available": bool(settings.openrouter_api_key)}


@router.post("/{match_id}/rich")
async def rich_match_analysis(match_id: str, request: RichAnalysisRequest, db: Session = Depends(get_db)) -> dict:
    user = _get_or_create_local_user(db)
    if not settings.openrouter_api_key:
        raise HTTPException(status_code=503, detail="Rich FanSphere analysis is not configured.")

    access = analysis_access_summary(db, user.id)
    if access["free_remaining"] == 0 and access["tokens"] <= 0:
        raise HTTPException(status_code=402, detail="Complete today's rewarded Daily Quiz to earn an Analysis Token.")

    try:
        explanation = await explain_match(
            home_team=request.home_team,
            away_team=request.away_team,
            competition=request.competition,
            model_outlook=request.model_outlook,
            comparison=request.comparison,
        )
    except AIAnalysisUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    unlocked = unlock_analysis(db, user.id, match_id)
    if not unlocked["unlocked"]:
        raise HTTPException(status_code=402, detail=unlocked["reason"])
    return {"analysis": explanation, "access": unlocked}
