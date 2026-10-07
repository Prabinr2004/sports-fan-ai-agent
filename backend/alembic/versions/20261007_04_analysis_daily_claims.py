"""Add unique daily rich-analysis allowance claims.

Revision ID: 20261007_04
Revises: 20261007_03
"""
from alembic import op
import sqlalchemy as sa

revision = "20261007_04"
down_revision = "20261007_03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "analysis_daily_claims",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("claim_date", sa.String(length=10), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "claim_date", name="uq_analysis_daily_claim"),
    )
    op.create_index("ix_analysis_daily_claims_user_id", "analysis_daily_claims", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_analysis_daily_claims_user_id", table_name="analysis_daily_claims")
    op.drop_table("analysis_daily_claims")
