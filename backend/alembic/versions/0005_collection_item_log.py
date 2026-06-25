"""collection item log

Revision ID: 0005_collection_item_log
Revises: 0004_holding_security_id
Create Date: 2026-06-25 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0005_collection_item_log"
down_revision = "0004_holding_security_id"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "collection_item_log",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("run_id", sa.Integer(), sa.ForeignKey("collection_run.id", ondelete="CASCADE"), nullable=False),
        sa.Column("etf_id", sa.Integer(), sa.ForeignKey("etf.id", ondelete="SET NULL"), nullable=True),
        sa.Column("ticker", sa.String(length=16), nullable=False),
        sa.Column("item_type", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_collection_item_log_run", "collection_item_log", ["run_id"])
    op.create_index("ix_collection_item_log_etf", "collection_item_log", ["etf_id"])
    op.create_index("ix_collection_item_log_ticker", "collection_item_log", ["ticker"])


def downgrade() -> None:
    op.drop_index("ix_collection_item_log_ticker", table_name="collection_item_log")
    op.drop_index("ix_collection_item_log_etf", table_name="collection_item_log")
    op.drop_index("ix_collection_item_log_run", table_name="collection_item_log")
    op.drop_table("collection_item_log")
