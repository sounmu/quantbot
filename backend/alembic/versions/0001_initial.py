"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-06-22 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "etf",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ticker", sa.String(length=16), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("issuer", sa.String(length=120), nullable=False),
        sa.Column("theme", sa.String(length=120), nullable=True),
        sa.Column("expense_ratio", sa.Float(), nullable=True),
        sa.Column("inception_date", sa.Date(), nullable=True),
        sa.Column("is_active_etf", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("currency", sa.String(length=8), nullable=False, server_default="USD"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("ticker", name="uq_etf_ticker"),
    )
    op.create_index("ix_etf_issuer", "etf", ["issuer"])
    op.create_index("ix_etf_theme", "etf", ["theme"])
    op.create_index("ix_etf_ticker", "etf", ["ticker"])

    op.create_table(
        "collection_run",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("job_name", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("items_processed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error", sa.Text(), nullable=True),
    )

    op.create_table(
        "etf_metric",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "etf_id", sa.Integer(), sa.ForeignKey("etf.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("as_of", sa.Date(), nullable=False),
        sa.Column("aum", sa.Float(), nullable=True),
        sa.Column("return_1m", sa.Float(), nullable=True),
        sa.Column("return_3m", sa.Float(), nullable=True),
        sa.Column("return_ytd", sa.Float(), nullable=True),
        sa.Column("return_1y", sa.Float(), nullable=True),
        sa.UniqueConstraint("etf_id", name="uq_etf_metric_etf_id"),
    )
    op.create_index("ix_etf_metric_etf_id", "etf_metric", ["etf_id"])

    op.create_table(
        "etf_price",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "etf_id", sa.Integer(), sa.ForeignKey("etf.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("open", sa.Float(), nullable=True),
        sa.Column("high", sa.Float(), nullable=True),
        sa.Column("low", sa.Float(), nullable=True),
        sa.Column("close", sa.Float(), nullable=False),
        sa.Column("nav", sa.Float(), nullable=True),
        sa.Column("volume", sa.BigInteger(), nullable=True),
        sa.UniqueConstraint("etf_id", "date", name="uq_etf_price_etf_date"),
    )
    op.create_index("ix_etf_price_date", "etf_price", ["date"])
    op.create_index("ix_etf_price_etf_id", "etf_price", ["etf_id"])

    op.create_table(
        "etf_holding",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "etf_id", sa.Integer(), sa.ForeignKey("etf.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("as_of_date", sa.Date(), nullable=False),
        sa.Column("holding_ticker", sa.String(length=32), nullable=True),
        sa.Column("holding_name", sa.String(length=255), nullable=False),
        sa.Column("weight", sa.Float(), nullable=False),
    )
    op.create_index("ix_etf_holding_etf_id", "etf_holding", ["etf_id"])


def downgrade() -> None:
    op.drop_index("ix_etf_holding_etf_id", table_name="etf_holding")
    op.drop_table("etf_holding")
    op.drop_index("ix_etf_price_etf_id", table_name="etf_price")
    op.drop_index("ix_etf_price_date", table_name="etf_price")
    op.drop_table("etf_price")
    op.drop_index("ix_etf_metric_etf_id", table_name="etf_metric")
    op.drop_table("etf_metric")
    op.drop_table("collection_run")
    op.drop_index("ix_etf_ticker", table_name="etf")
    op.drop_index("ix_etf_theme", table_name="etf")
    op.drop_index("ix_etf_issuer", table_name="etf")
    op.drop_table("etf")
