"""Store generated daily quiz snapshots.

Revision ID: 20261007_02
Revises: 20261007_01
"""
from alembic import op
import sqlalchemy as sa

revision = "20261007_02"
down_revision = "20261007_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "daily_quiz_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("quiz_date", sa.String(length=10), nullable=False),
        sa.Column("level", sa.Integer(), nullable=False),
        sa.Column("theme", sa.String(length=80), nullable=False),
        sa.Column("team_provider_id", sa.String(length=80), nullable=True),
        sa.Column("team_name", sa.String(length=160), nullable=True),
        sa.Column("questions_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "quiz_date", name="uq_daily_quiz_snapshot"),
    )
    op.create_index("ix_daily_quiz_snapshots_user_id", "daily_quiz_snapshots", ["user_id"])
    op.create_index("ix_daily_quiz_snapshots_quiz_date", "daily_quiz_snapshots", ["quiz_date"])


def downgrade() -> None:
    op.drop_index("ix_daily_quiz_snapshots_quiz_date", table_name="daily_quiz_snapshots")
    op.drop_index("ix_daily_quiz_snapshots_user_id", table_name="daily_quiz_snapshots")
    op.drop_table("daily_quiz_snapshots")
