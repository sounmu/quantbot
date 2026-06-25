"""holding security identifier

Revision ID: 0004_holding_security_id
Revises: 0003_holding_key_lock
Create Date: 2026-06-24 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0004_holding_security_id"
down_revision = "0003_holding_key_lock"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("etf_holding", sa.Column("security_id", sa.String(length=64), nullable=True))
    op.add_column(
        "etf_holding_change", sa.Column("security_id", sa.String(length=64), nullable=True)
    )
    op.create_index("ix_etf_holding_security_id", "etf_holding", ["security_id"])


def downgrade() -> None:
    op.drop_index("ix_etf_holding_security_id", table_name="etf_holding")
    with op.batch_alter_table("etf_holding_change") as batch_op:
        batch_op.drop_column("security_id")
    with op.batch_alter_table("etf_holding") as batch_op:
        batch_op.drop_column("security_id")
