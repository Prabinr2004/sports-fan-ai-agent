"""Persist completed match prediction results.

Revision ID: 20261007_01
Revises:
"""
from alembic import op
import sqlalchemy as sa

revision = "20261007_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("user_match_predictions") as batch_op:
        batch_op.add_column(sa.Column("actual_outcome", sa.String(length=10), nullable=True))
        batch_op.add_column(sa.Column("result_status", sa.String(length=12), nullable=False, server_default="PENDING"))
        batch_op.add_column(sa.Column("home_score", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("away_score", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("result_checked_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("user_match_predictions") as batch_op:
        batch_op.drop_column("result_checked_at")
        batch_op.drop_column("away_score")
        batch_op.drop_column("home_score")
        batch_op.drop_column("result_status")
        batch_op.drop_column("actual_outcome")
