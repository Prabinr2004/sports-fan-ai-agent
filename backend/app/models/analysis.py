from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


class AnalysisTokenEvent(Base):
    __tablename__ = "analysis_token_events"
    __table_args__ = (
        UniqueConstraint("user_id", "source_type", "source_id", name="uq_analysis_token_event_source"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    amount: Mapped[int] = mapped_column(Integer)
    source_type: Mapped[str] = mapped_column(String(50), index=True)
    source_id: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MatchAnalysisUnlock(Base):
    __tablename__ = "match_analysis_unlocks"
    __table_args__ = (
        UniqueConstraint("user_id", "match_id", name="uq_user_match_analysis_unlock"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    match_id: Mapped[str] = mapped_column(String(80), index=True)
    unlock_source: Mapped[str] = mapped_column(String(20))
    unlock_date: Mapped[str] = mapped_column(String(10), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
