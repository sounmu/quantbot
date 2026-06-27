"""signal forward return outcomes

Revision ID: 0009_signal_outcome
Revises: 0008_signal_daily
Create Date: 2026-06-27 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0009_signal_outcome"
down_revision = "0008_signal_daily"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "signal_outcome",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "security_key",
            sa.String(length=320),
            sa.ForeignKey("security.security_key", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("as_of_date", sa.Date(), nullable=False),
        sa.Column("horizon_days", sa.Integer(), nullable=False),
        sa.Column(
            "benchmark_key",
            sa.String(length=320),
            sa.ForeignKey("security.security_key", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("stock_return", sa.Float(), nullable=False),
        sa.Column("benchmark_return", sa.Float(), nullable=False),
        sa.Column("excess_return", sa.Float(), nullable=False),
        sa.Column("signal_score", sa.Float(), nullable=False),
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
        sa.UniqueConstraint(
            "security_key",
            "as_of_date",
            "horizon_days",
            "benchmark_key",
            name="uq_signal_outcome_signal_horizon_benchmark",
        ),
    )
    op.create_index("ix_signal_outcome_security_key", "signal_outcome", ["security_key"])
    op.create_index("ix_signal_outcome_as_of_date", "signal_outcome", ["as_of_date"])
    op.create_index("ix_signal_outcome_benchmark_key", "signal_outcome", ["benchmark_key"])
    op.create_index("ix_signal_outcome_horizon", "signal_outcome", ["horizon_days"])
    op.create_index(
        "ix_signal_outcome_security_date",
        "signal_outcome",
        ["security_key", "as_of_date"],
    )


def downgrade() -> None:
    op.drop_index("ix_signal_outcome_security_date", table_name="signal_outcome")
    op.drop_index("ix_signal_outcome_horizon", table_name="signal_outcome")
    op.drop_index("ix_signal_outcome_benchmark_key", table_name="signal_outcome")
    op.drop_index("ix_signal_outcome_as_of_date", table_name="signal_outcome")
    op.drop_index("ix_signal_outcome_security_key", table_name="signal_outcome")
    op.drop_table("signal_outcome")
