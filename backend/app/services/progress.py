from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.progress import DailyActivity, XPEvent

XP_PER_LEVEL = 500


def level_from_xp(total_xp: int) -> dict:
    level = total_xp // XP_PER_LEVEL + 1
    level_start = (level - 1) * XP_PER_LEVEL
    progress_xp = total_xp - level_start
    return {
        "level": level,
        "total_xp": total_xp,
        "xp_into_level": progress_xp,
        "xp_for_next_level": XP_PER_LEVEL,
        "progress_percent": round((progress_xp / XP_PER_LEVEL) * 100, 1),
    }


def total_xp(db: Session, user_id: int) -> int:
    return int(db.scalar(select(func.coalesce(func.sum(XPEvent.amount), 0)).where(XPEvent.user_id == user_id, XPEvent.amount > 0)) or 0)


def record_activity_day(db: Session, user_id: int, activity_date: date | None = None) -> None:
    day = activity_date or date.today()
    existing = db.scalar(select(DailyActivity).where(DailyActivity.user_id == user_id, DailyActivity.activity_date == day))
    if not existing:
        db.add(DailyActivity(user_id=user_id, activity_date=day))


def streak_summary(db: Session, user_id: int, today: date | None = None) -> dict:
    current_day = today or date.today()
    days = list(db.scalars(select(DailyActivity.activity_date).where(DailyActivity.user_id == user_id).order_by(DailyActivity.activity_date.desc())).all())
    if not days:
        return {"current_streak": 0, "longest_streak": 0, "last_active_date": None}

    unique_days = sorted(set(days))
    longest = 1
    run = 1
    for previous, current in zip(unique_days, unique_days[1:]):
        if current == previous + timedelta(days=1):
            run += 1
            longest = max(longest, run)
        else:
            run = 1

    latest = unique_days[-1]
    if latest not in {current_day, current_day - timedelta(days=1)}:
        current = 0
    else:
        current = 1
        cursor = latest
        day_set = set(unique_days)
        while cursor - timedelta(days=1) in day_set:
            current += 1
            cursor -= timedelta(days=1)

    return {"current_streak": current, "longest_streak": longest, "last_active_date": latest.isoformat()}


def progress_summary(db: Session, user_id: int) -> dict:
    return {**level_from_xp(total_xp(db, user_id)), **streak_summary(db, user_id)}
