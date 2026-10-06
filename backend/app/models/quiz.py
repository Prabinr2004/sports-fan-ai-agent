from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


class DailyQuizSnapshot(Base):
    __tablename__ = "daily_quiz_snapshots"
    __table_args__ = (
        UniqueConstraint("user_id", "quiz_date", name="uq_daily_quiz_snapshot"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    quiz_date: Mapped[str] = mapped_column(String(10), index=True)
    level: Mapped[int] = mapped_column(Integer)
    theme: Mapped[str] = mapped_column(String(80))
    team_provider_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    team_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    questions_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
