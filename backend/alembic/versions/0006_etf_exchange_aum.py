"""etf exchange and signal universe metadata

Revision ID: 0006_etf_exchange_aum
Revises: 0005_collection_item_log
Create Date: 2026-06-27 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0006_etf_exchange_aum"
down_revision = "0005_collection_item_log"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("etf", sa.Column("exchange", sa.String(length=64), nullable=True))
    op.add_column("etf", sa.Column("aum", sa.Float(), nullable=True))
    op.add_column(
        "etf",
        sa.Column(
            "in_signal_universe",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "etf", sa.Column("signal_universe_reason", sa.String(length=120), nullable=True)
    )
    op.create_index("ix_etf_exchange", "etf", ["exchange"])
    op.create_index("ix_etf_in_signal_universe", "etf", ["in_signal_universe"])
    op.execute(
        """
        UPDATE etf
        SET aum = (
            SELECT etf_metric.aum
            FROM etf_metric
            WHERE etf_metric.etf_id = etf.id
        )
        """
    )


def downgrade() -> None:
    op.drop_index("ix_etf_in_signal_universe", table_name="etf")
    op.drop_index("ix_etf_exchange", table_name="etf")
    with op.batch_alter_table("etf") as batch_op:
        batch_op.drop_column("signal_universe_reason")
        batch_op.drop_column("in_signal_universe")
        batch_op.drop_column("aum")
        batch_op.drop_column("exchange")
