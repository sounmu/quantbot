"""holdings snapshots and changes

Revision ID: 0002_holdings_change
Revises: 0001_initial
Create Date: 2026-06-22 00:00:01.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0002_holdings_change"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("etf") as batch_op:
        batch_op.add_column(
            sa.Column("discloses_daily", sa.Boolean(), nullable=False, server_default=sa.true())
        )

    with op.batch_alter_table("etf_holding") as batch_op:
        batch_op.add_column(sa.Column("shares", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("market_value", sa.Float(), nullable=True))
        batch_op.create_unique_constraint(
            "uq_etf_holding_snapshot_row",
            ["etf_id", "as_of_date", "holding_ticker", "holding_name"],
        )

    op.create_index("ix_etf_holding_as_of_date", "etf_holding", ["as_of_date"])
    op.create_index("ix_etf_holding_holding_ticker", "etf_holding", ["holding_ticker"])

    op.create_table(
        "etf_holding_change",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "etf_id", sa.Integer(), sa.ForeignKey("etf.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("as_of_date", sa.Date(), nullable=False),
        sa.Column("prev_date", sa.Date(), nullable=True),
        sa.Column("holding_ticker", sa.String(length=32), nullable=True),
        sa.Column("holding_name", sa.String(length=255), nullable=False),
        sa.Column("change_type", sa.String(length=24), nullable=False),
        sa.Column("shares_before", sa.Float(), nullable=True),
        sa.Column("shares_after", sa.Float(), nullable=True),
        sa.Column("shares_delta", sa.Float(), nullable=True),
        sa.Column("shares_delta_pct", sa.Float(), nullable=True),
        sa.Column("weight_before", sa.Float(), nullable=True),
        sa.Column("weight_after", sa.Float(), nullable=True),
        sa.Column("weight_delta", sa.Float(), nullable=True),
        sa.UniqueConstraint(
            "etf_id",
            "as_of_date",
            "holding_ticker",
            "holding_name",
            name="uq_etf_holding_change_snapshot_row",
        ),
    )
    op.create_index("ix_etf_holding_change_etf_id", "etf_holding_change", ["etf_id"])
    op.create_index(
        "ix_etf_holding_change_etf_date",
        "etf_holding_change",
        ["etf_id", "as_of_date"],
    )
    op.create_index(
        "ix_etf_holding_change_position",
        "etf_holding_change",
        ["etf_id", "holding_ticker", "as_of_date"],
    )
    op.create_index("ix_etf_holding_change_date", "etf_holding_change", ["as_of_date"])


def downgrade() -> None:
    op.drop_index("ix_etf_holding_change_date", table_name="etf_holding_change")
    op.drop_index("ix_etf_holding_change_position", table_name="etf_holding_change")
    op.drop_index("ix_etf_holding_change_etf_date", table_name="etf_holding_change")
    op.drop_index("ix_etf_holding_change_etf_id", table_name="etf_holding_change")
    op.drop_table("etf_holding_change")

    op.drop_index("ix_etf_holding_holding_ticker", table_name="etf_holding")
    op.drop_index("ix_etf_holding_as_of_date", table_name="etf_holding")

    with op.batch_alter_table("etf_holding") as batch_op:
        batch_op.drop_constraint("uq_etf_holding_snapshot_row", type_="unique")
        batch_op.drop_column("market_value")
        batch_op.drop_column("shares")

    with op.batch_alter_table("etf") as batch_op:
        batch_op.drop_column("discloses_daily")
