from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.auth import require_user
from app.database.session import get_db
from app.models.user import User
from app.models.gems import GemEvent
from app.services.gems import exchange_xp, gem_balance, spendable_xp, XP_PER_GEM

router = APIRouter(prefix="/economy", tags=["economy"])

class ExchangeRequest(BaseModel):
    gems: int = Field(ge=1, le=20)

@router.get("")
def get_economy(request: Request, db: Session = Depends(get_db)) -> dict:
    user = require_user(request, db)
    return {"gems": gem_balance(db, user.id), "spendable_xp": spendable_xp(db, user.id),
            "xp_per_gem": XP_PER_GEM}

@router.post("/exchange")
def exchange(body: ExchangeRequest, request: Request, db: Session = Depends(get_db)) -> dict:
    user = require_user(request, db)
    db.scalar(select(User).where(User.id == user.id).with_for_update())
    try:
        return exchange_xp(db, user.id, body.gems)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@router.get("/history")
def history(request: Request, db: Session = Depends(get_db)) -> dict:
    user = require_user(request, db)
    events = db.scalars(select(GemEvent).where(GemEvent.user_id == user.id).order_by(GemEvent.id.desc()).limit(30)).all()
    return {"events": [{"amount": event.amount, "source": event.source_type,
                        "created_at": event.created_at.isoformat() if event.created_at else None}
                       for event in events]}
