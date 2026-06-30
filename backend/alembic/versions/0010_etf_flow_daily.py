"""etf daily fund flow estimates

Revision ID: 0010_etf_flow_daily
Revises: 0009_signal_outcome
Create Date: 2026-06-28 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0010_etf_flow_daily"
down_revision = "0009_signal_outcome"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "etf_flow_daily",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "etf_id",
            sa.Integer(),
            sa.ForeignKey("etf.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("as_of_date", sa.Date(), nullable=False),
        sa.Column("prev_date", sa.Date(), nullable=False),
        sa.Column("net_flow", sa.Float(), nullable=False),
        sa.Column("flow_rate", sa.Float(), nullable=False),
        sa.Column("active_buy", sa.Float(), nullable=False),
        sa.Column("active_sell", sa.Float(), nullable=False),
        sa.Column("turnover", sa.Float(), nullable=False),
        sa.Column("creation_r2", sa.Float(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("etf_id", "as_of_date", name="uq_etf_flow_daily_etf_date"),
    )
    op.create_index("ix_etf_flow_daily_etf_id", "etf_flow_daily", ["etf_id"])
    op.create_index("ix_etf_flow_daily_as_of_date", "etf_flow_daily", ["as_of_date"])
    op.create_index(
        "ix_etf_flow_daily_etf_date",
        "etf_flow_daily",
        ["etf_id", "as_of_date"],
    )


def downgrade() -> None:
    op.drop_index("ix_etf_flow_daily_etf_date", table_name="etf_flow_daily")
    op.drop_index("ix_etf_flow_daily_as_of_date", table_name="etf_flow_daily")
    op.drop_index("ix_etf_flow_daily_etf_id", table_name="etf_flow_daily")
    op.drop_table("etf_flow_daily")
