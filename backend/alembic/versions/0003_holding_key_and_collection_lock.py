"""holding key and collection lock

Revision ID: 0003_holding_key_lock
Revises: 0002_holdings_change
Create Date: 2026-06-23 00:00:00.000000
"""

from __future__ import annotations

import re
from typing import Any

from alembic import op
import sqlalchemy as sa


revision = "0003_holding_key_lock"
down_revision = "0002_holdings_change"
branch_labels = None
depends_on = None


_CASH_TOKENS = {"", "--", "-", "CASH", "USD", "US DOLLAR", "DOLLAR", "MONEYMARKET"}
_CASH_NAME_TOKENS = {"CASH", "CASHEQUIVALENTS", "CASHANDEQUIVALENTS", "USD", "USDOLLAR"}


def upgrade() -> None:
    op.add_column("etf_holding", sa.Column("holding_key", sa.String(length=320), nullable=True))
    op.add_column(
        "etf_holding_change", sa.Column("holding_key", sa.String(length=320), nullable=True)
    )
    _backfill_holding_keys()

    with op.batch_alter_table("etf_holding") as batch_op:
        batch_op.alter_column("holding_key", existing_type=sa.String(length=320), nullable=False)
        batch_op.drop_constraint("uq_etf_holding_snapshot_row", type_="unique")
        batch_op.create_unique_constraint(
            "uq_etf_holding_snapshot_key",
            ["etf_id", "as_of_date", "holding_key"],
        )

    with op.batch_alter_table("etf_holding_change") as batch_op:
        batch_op.alter_column("holding_key", existing_type=sa.String(length=320), nullable=False)
        batch_op.drop_constraint("uq_etf_holding_change_snapshot_row", type_="unique")
        batch_op.create_unique_constraint(
            "uq_etf_holding_change_snapshot_key",
            ["etf_id", "as_of_date", "holding_key"],
        )

    op.create_index("ix_etf_holding_holding_key", "etf_holding", ["holding_key"])
    op.create_index(
        "ix_etf_holding_position_key",
        "etf_holding",
        ["etf_id", "holding_key", "as_of_date"],
    )
    op.drop_index("ix_etf_holding_change_position", table_name="etf_holding_change")
    op.create_index(
        "ix_etf_holding_change_position",
        "etf_holding_change",
        ["etf_id", "holding_key", "as_of_date"],
    )

    op.create_table(
        "collection_lock",
        sa.Column("lock_key", sa.String(length=120), primary_key=True),
        sa.Column("acquired_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("collection_lock")
    op.drop_index("ix_etf_holding_change_position", table_name="etf_holding_change")
    op.create_index(
        "ix_etf_holding_change_position",
        "etf_holding_change",
        ["etf_id", "holding_ticker", "as_of_date"],
    )
    op.drop_index("ix_etf_holding_position_key", table_name="etf_holding")
    op.drop_index("ix_etf_holding_holding_key", table_name="etf_holding")

    with op.batch_alter_table("etf_holding_change") as batch_op:
        batch_op.drop_constraint("uq_etf_holding_change_snapshot_key", type_="unique")
        batch_op.create_unique_constraint(
            "uq_etf_holding_change_snapshot_row",
            ["etf_id", "as_of_date", "holding_ticker", "holding_name"],
        )
        batch_op.drop_column("holding_key")

    with op.batch_alter_table("etf_holding") as batch_op:
        batch_op.drop_constraint("uq_etf_holding_snapshot_key", type_="unique")
        batch_op.create_unique_constraint(
            "uq_etf_holding_snapshot_row",
            ["etf_id", "as_of_date", "holding_ticker", "holding_name"],
        )
        batch_op.drop_column("holding_key")


def _backfill_holding_keys() -> None:
    bind = op.get_bind()
    for table in ("etf_holding", "etf_holding_change"):
        rows = bind.execute(
            sa.text(f"select id, holding_ticker, holding_name from {table}")
        ).mappings()
        for row in rows:
            bind.execute(
                sa.text(f"update {table} set holding_key = :holding_key where id = :id"),
                {"id": row["id"], "holding_key": _holding_key(row)},
            )


def _holding_key(row: dict[str, Any]) -> str:
    ticker = row["holding_ticker"]
    if ticker is not None:
        clean_ticker = str(ticker).strip().upper()
        if clean_ticker not in _CASH_TOKENS:
            return clean_ticker

    normalized_name = re.sub(r"[^A-Z0-9]", "", str(row["holding_name"]).upper())
    if not normalized_name or normalized_name in _CASH_NAME_TOKENS:
        return f"IGNORED:{row['id']}"
    return f"NAME:{normalized_name}"
