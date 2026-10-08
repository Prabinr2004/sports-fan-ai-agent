from datetime import date

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.analysis import AnalysisDailyClaim, AnalysisTokenEvent, MatchAnalysisUnlock
from app.models.user import User
from app.services.gems import gem_balance, spendable_xp, spend_analysis_gems, XP_PER_GEM, GEMS_PER_ANALYSIS, MAX_EXTRA_ANALYSES


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
    free_used = db.scalar(select(AnalysisDailyClaim).where(
        AnalysisDailyClaim.user_id == user_id,
        AnalysisDailyClaim.claim_date == today,
    )) is not None
    extras_used = int(db.scalar(select(func.count(MatchAnalysisUnlock.id)).where(
        MatchAnalysisUnlock.user_id == user_id,
        MatchAnalysisUnlock.unlock_date == today,
        MatchAnalysisUnlock.unlock_source == "GEMS",
    )) or 0)
    return {
        "tokens": token_balance(db, user_id),
        "gems": gem_balance(db, user_id),
        "spendable_xp": spendable_xp(db, user_id),
        "xp_per_gem": XP_PER_GEM,
        "gems_per_analysis": GEMS_PER_ANALYSIS,
        "extra_remaining": max(0, MAX_EXTRA_ANALYSES - extras_used),
        "extra_daily_limit": MAX_EXTRA_ANALYSES,
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
    # Serialize allowance/token decisions per user on databases that support row locks.
    db.scalar(select(User).where(User.id == user_id).with_for_update())
    free_used = db.scalar(select(AnalysisDailyClaim).where(
        AnalysisDailyClaim.user_id == user_id,
        AnalysisDailyClaim.claim_date == today,
    )) is not None

    if not free_used:
        source = "FREE_DAILY"
        db.add(AnalysisDailyClaim(user_id=user_id, claim_date=today))
    else:
        extras_used = int(db.scalar(select(func.count(MatchAnalysisUnlock.id)).where(
            MatchAnalysisUnlock.user_id == user_id,
            MatchAnalysisUnlock.unlock_date == today,
            MatchAnalysisUnlock.unlock_source == "GEMS",
        )) or 0)
        if extras_used >= MAX_EXTRA_ANALYSES:
            return {"unlocked": False, "reason": "Daily limit reached: 1 free plus 3 gem-unlocked analyses.", **analysis_access_summary(db, user_id)}
        try:
            spend_analysis_gems(db, user_id, match_id)
        except ValueError as exc:
            return {"unlocked": False, "reason": str(exc), **analysis_access_summary(db, user_id)}
        source = "GEMS"

    db.add(MatchAnalysisUnlock(
        user_id=user_id,
        match_id=match_id,
        unlock_source=source,
        unlock_date=today,
        analysis_text=analysis_text,
    ))
    db.commit()
    return {"unlocked": True, "source": source, "charged": True, **analysis_access_summary(db, user_id)}
