from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.profile import DEMO_EMAIL, _get_or_create_local_user
from app.database.session import get_db
from app.models.progress import XPEvent
from app.models.user import User
from app.services.progress import level_from_xp

router = APIRouter(prefix="/leaderboard", tags=["leaderboard"])


@router.get("")
def leaderboard(db: Session = Depends(get_db)) -> dict:
    current_user = _get_or_create_local_user(db)
    xp_total = func.coalesce(func.sum(XPEvent.amount), 0).label("total_xp")
    rows = db.execute(
        select(User, xp_total)
        .outerjoin(XPEvent, XPEvent.user_id == User.id)
        .group_by(User.id)
        .order_by(xp_total.desc(), User.created_at.asc())
        .limit(50)
    ).all()

    entries = []
    for rank, (user, total_xp) in enumerate(rows, start=1):
        total = int(total_xp or 0)
        level = level_from_xp(total)["level"]
        entries.append({
            "rank": rank,
            "user_id": user.id,
            "display_name": user.display_name,
            "total_xp": total,
            "level": level,
            "is_current_user": user.id == current_user.id,
        })

    return {
        "entries": entries,
        "current_user_email": DEMO_EMAIL,
        "mode": "local-development",
        "notice": "The leaderboard currently ranks real local accounts only. More users will appear after authentication is added.",
    }
