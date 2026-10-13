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


class QuizProgressState(Base):
    """Quiz-only reset boundary; does not modify XP, Gems, or streak records."""
    __tablename__ = "quiz_progress_states"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    reset_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    selected_level: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    # Existing daily quiz XP remains in the ledger; only newer snapshots
    # count toward progression. The daily reward cap remains date-based.


class QuizRoundCompletion(Base):
    """Progress independent of historical XP and legacy quiz snapshots."""
    __tablename__ = "quiz_round_completions"
    __table_args__ = (
        UniqueConstraint("user_id", "quiz_date", name="uq_quiz_round_user_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    quiz_date: Mapped[str] = mapped_column(String(10), index=True)
    level: Mapped[int] = mapped_column(Integer, nullable=False)
    team_provider_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    question_ids_json: Mapped[str] = mapped_column(Text, nullable=False)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
