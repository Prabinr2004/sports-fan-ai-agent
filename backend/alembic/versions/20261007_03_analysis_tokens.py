"""Add analysis token economy.

Revision ID: 20261007_03
Revises: 20261007_02
"""
from alembic import op
import sqlalchemy as sa

revision = "20261007_03"
down_revision = "20261007_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "analysis_token_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("source_type", sa.String(length=50), nullable=False),
        sa.Column("source_id", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "source_type", "source_id", name="uq_analysis_token_event_source"),
    )
    op.create_index("ix_analysis_token_events_user_id", "analysis_token_events", ["user_id"])
    op.create_index("ix_analysis_token_events_source_type", "analysis_token_events", ["source_type"])

    op.create_table(
        "match_analysis_unlocks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("match_id", sa.String(length=80), nullable=False),
        sa.Column("unlock_source", sa.String(length=20), nullable=False),
        sa.Column("unlock_date", sa.String(length=10), nullable=False),
        sa.Column("analysis_text", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "match_id", name="uq_user_match_analysis_unlock"),
    )
    op.create_index("ix_match_analysis_unlocks_user_id", "match_analysis_unlocks", ["user_id"])
    op.create_index("ix_match_analysis_unlocks_match_id", "match_analysis_unlocks", ["match_id"])
    op.create_index("ix_match_analysis_unlocks_unlock_date", "match_analysis_unlocks", ["unlock_date"])


def downgrade() -> None:
    op.drop_index("ix_match_analysis_unlocks_unlock_date", table_name="match_analysis_unlocks")
    op.drop_index("ix_match_analysis_unlocks_match_id", table_name="match_analysis_unlocks")
    op.drop_index("ix_match_analysis_unlocks_user_id", table_name="match_analysis_unlocks")
    op.drop_table("match_analysis_unlocks")
    op.drop_index("ix_analysis_token_events_source_type", table_name="analysis_token_events")
    op.drop_index("ix_analysis_token_events_user_id", table_name="analysis_token_events")
    op.drop_table("analysis_token_events")
