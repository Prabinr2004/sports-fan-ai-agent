"""One-time, owner-controlled migration of legacy local demo progress.

Run only from the trusted machine that owns the existing SQLite database.
This module deliberately exposes no HTTP endpoint.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.analysis import AnalysisDailyClaim, AnalysisTokenEvent, MatchAnalysisUnlock
from app.models.prediction import UserMatchPrediction
from app.models.progress import DailyActivity, XPEvent
from app.models.quiz import DailyQuizSnapshot
from app.models.user import User, UserFavoriteTeam

DEMO_EMAIL = "local@fansphere.dev"

# Uniqueness scopes used to avoid overwriting existing registered-account records.
TABLES = (
    (UserFavoriteTeam, ("team_id",)),
    (XPEvent, ("source_type", "source_id")),
    (DailyActivity, ("activity_date",)),
    (UserMatchPrediction, ("match_id",)),
    (DailyQuizSnapshot, ("quiz_date",)),
    (AnalysisTokenEvent, ("source_type", "source_id")),
    (MatchAnalysisUnlock, ("match_id",)),
    (AnalysisDailyClaim, ("claim_date",)),
)


def migrate_demo_progress(db: Session, target_email: str, *, apply: bool = False) -> dict:
    """Preview by default; transfer only after explicit local confirmation."""
    email = target_email.strip().lower()
    source = db.scalar(select(User).where(User.email == DEMO_EMAIL))
    target = db.scalar(select(User).where(User.email == email))
    if source is None:
        raise ValueError("No legacy demo account exists in this database.")
    if target is None or target.id == source.id:
        raise ValueError("Register and sign into a different account before migration.")
    if not target.password_hash.startswith("pbkdf2_sha256$"):
        raise ValueError("Target must be a registered account.")
    if source.primary_team_id and target.primary_team_id and source.primary_team_id != target.primary_team_id:
        raise ValueError("Target already has a different primary team. Resolve this before migration.")

    counts = {}
    for model, key_columns in TABLES:
        old = db.scalars(select(model).where(model.user_id == source.id)).all()
        existing = {
            tuple(getattr(row, column) for column in key_columns)
            for row in db.scalars(select(model).where(model.user_id == target.id)).all()
        }
        conflicts = [
            row for row in old
            if tuple(getattr(row, column) for column in key_columns) in existing
        ]
        if conflicts:
            raise ValueError(f"Migration stopped: {len(conflicts)} overlapping {model.__tablename__} records. Nothing transferred.")
        counts[model.__tablename__] = len(old)

    if apply:
        if source.primary_team_id and not target.primary_team_id:
            target.primary_team_id = source.primary_team_id
        for model, _ in TABLES:
            for row in db.scalars(select(model).where(model.user_id == source.id)).all():
                row.user_id = target.id
        db.commit()
    return {"source": DEMO_EMAIL, "target": email, "applied": apply, "records": counts,
            "primary_team_transfer": bool(source.primary_team_id and not target.primary_team_id)}
