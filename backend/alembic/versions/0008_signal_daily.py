"""daily cross-etf signals

Revision ID: 0008_signal_daily
Revises: 0007_security_price
Create Date: 2026-06-27 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0008_signal_daily"
down_revision = "0007_security_price"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "signal_daily",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "security_key",
            sa.String(length=320),
            sa.ForeignKey("security.security_key", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("as_of_date", sa.Date(), nullable=False),
        sa.Column("n_buying", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("n_selling", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("net_shares_flow", sa.Float(), nullable=True),
        sa.Column("net_dollar_flow", sa.Float(), nullable=True),
        sa.Column("conviction_score", sa.Float(), nullable=False),
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
        sa.UniqueConstraint("security_key", "as_of_date", name="uq_signal_daily_security_date"),
    )
    op.create_index("ix_signal_daily_security_key", "signal_daily", ["security_key"])
    op.create_index("ix_signal_daily_as_of_date", "signal_daily", ["as_of_date"])
    op.create_index(
        "ix_signal_daily_date_score",
        "signal_daily",
        ["as_of_date", "conviction_score"],
    )


def downgrade() -> None:
    op.drop_index("ix_signal_daily_date_score", table_name="signal_daily")
    op.drop_index("ix_signal_daily_as_of_date", table_name="signal_daily")
    op.drop_index("ix_signal_daily_security_key", table_name="signal_daily")
    op.drop_table("signal_daily")
