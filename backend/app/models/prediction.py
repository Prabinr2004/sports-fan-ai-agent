from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


class UserMatchPrediction(Base):
    __tablename__ = "user_match_predictions"
    __table_args__ = (
        UniqueConstraint("user_id", "match_id", name="uq_user_match_prediction"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    match_id: Mapped[str] = mapped_column(String(80), index=True)
    home_team_name: Mapped[str] = mapped_column(String(160))
    away_team_name: Mapped[str] = mapped_column(String(160))
    predicted_outcome: Mapped[str] = mapped_column(String(10))
    kickoff_utc: Mapped[str | None] = mapped_column(String(40), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
