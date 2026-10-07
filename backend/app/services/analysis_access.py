from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.analysis import AnalysisTokenEvent, MatchAnalysisUnlock


def token_balance(db: Session, user_id: int) -> int:
    return int(db.scalar(select(func.coalesce(func.sum(AnalysisTokenEvent.amount), 0)).where(
        AnalysisTokenEvent.user_id == user_id
    )) or 0)


def grant_quiz_token(db: Session, user_id: int, quiz_date: str) -> bool:
    existing = db.scalar(select(AnalysisTokenEvent).where(
        AnalysisTokenEvent.user_id == user_id,
        AnalysisTokenEvent.source_type == "daily_quiz",
        AnalysisTokenEvent.source_id == quiz_date,
    ))
    if existing:
        return False
    db.add(AnalysisTokenEvent(
        user_id=user_id,
        amount=1,
        source_type="daily_quiz",
        source_id=quiz_date,
    ))
    return True


def analysis_access_summary(db: Session, user_id: int) -> dict:
    today = date.today().isoformat()
    free_used = db.scalar(select(MatchAnalysisUnlock).where(
        MatchAnalysisUnlock.user_id == user_id,
        MatchAnalysisUnlock.unlock_source == "FREE_DAILY",
        MatchAnalysisUnlock.unlock_date == today,
    )) is not None
    return {
        "tokens": token_balance(db, user_id),
        "free_remaining": 0 if free_used else 1,
        "date": today,
    }


def unlock_analysis(db: Session, user_id: int, match_id: str, analysis_text: str | None = None) -> dict:
    existing = db.scalar(select(MatchAnalysisUnlock).where(
        MatchAnalysisUnlock.user_id == user_id,
        MatchAnalysisUnlock.match_id == match_id,
    ))
    if existing:
        if analysis_text and not existing.analysis_text:
            existing.analysis_text = analysis_text
            db.commit()
        return {"unlocked": True, "source": existing.unlock_source, "charged": False, **analysis_access_summary(db, user_id)}

    today = date.today().isoformat()
    free_used = db.scalar(select(MatchAnalysisUnlock).where(
        MatchAnalysisUnlock.user_id == user_id,
        MatchAnalysisUnlock.unlock_source == "FREE_DAILY",
        MatchAnalysisUnlock.unlock_date == today,
    )) is not None

    if not free_used:
        source = "FREE_DAILY"
    elif token_balance(db, user_id) > 0:
        source = "TOKEN"
        db.add(AnalysisTokenEvent(
            user_id=user_id,
            amount=-1,
            source_type="match_analysis",
            source_id=match_id,
        ))
    else:
        return {"unlocked": False, "reason": "Complete today's rewarded Daily Quiz to earn an Analysis Token.", **analysis_access_summary(db, user_id)}

    db.add(MatchAnalysisUnlock(
        user_id=user_id,
        match_id=match_id,
        unlock_source=source,
        unlock_date=today,
        analysis_text=analysis_text,
    ))
    db.commit()
    return {"unlocked": True, "source": source, "charged": True, **analysis_access_summary(db, user_id)}
