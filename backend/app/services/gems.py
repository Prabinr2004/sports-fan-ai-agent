from datetime import date
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.models.gems import GemEvent
from app.models.progress import XPEvent

XP_PER_GEM = 200
GEMS_PER_ANALYSIS = 2
MAX_EXTRA_ANALYSES = 3

def gem_balance(db: Session, user_id: int) -> int:
    return int(db.scalar(select(func.coalesce(func.sum(GemEvent.amount), 0)).where(GemEvent.user_id == user_id)) or 0)

def spent_xp(db: Session, user_id: int) -> int:
    return -int(db.scalar(select(func.coalesce(func.sum(XPEvent.amount), 0)).where(
        XPEvent.user_id == user_id, XPEvent.source_type == "gem_exchange"
    )) or 0)

def spendable_xp(db: Session, user_id: int) -> int:
    earned = int(db.scalar(select(func.coalesce(func.sum(XPEvent.amount), 0)).where(
        XPEvent.user_id == user_id, XPEvent.amount > 0
    )) or 0)
    return max(0, earned - spent_xp(db, user_id))

def exchange_xp(db: Session, user_id: int, quantity: int) -> dict:
    if quantity < 1 or quantity > 20:
        raise ValueError("Exchange between 1 and 20 gems at a time.")
    cost = quantity * XP_PER_GEM
    if spendable_xp(db, user_id) < cost:
        raise ValueError("Not enough available XP for this exchange.")
    reference = uuid4().hex
    db.add(XPEvent(user_id=user_id, amount=-cost, source_type="gem_exchange", source_id=reference))
    db.add(GemEvent(user_id=user_id, amount=quantity, source_type="xp_exchange", source_id=reference))
    db.commit()
    return {"gems": gem_balance(db, user_id), "spendable_xp": spendable_xp(db, user_id), "exchanged": quantity, "xp_spent": cost}

def spend_analysis_gems(db: Session, user_id: int, match_id: str) -> None:
    if gem_balance(db, user_id) < GEMS_PER_ANALYSIS:
        raise ValueError("Not enough gems. Exchange XP to unlock another analysis.")
    db.add(GemEvent(user_id=user_id, amount=-GEMS_PER_ANALYSIS, source_type="match_analysis", source_id=match_id))
