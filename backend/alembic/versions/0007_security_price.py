"""security master and underlying prices

Revision ID: 0007_security_price
Revises: 0006_etf_exchange_aum
Create Date: 2026-06-27 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0007_security_price"
down_revision = "0006_etf_exchange_aum"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "security",
        sa.Column("security_key", sa.String(length=320), nullable=False),
        sa.Column("ticker", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("first_seen", sa.Date(), nullable=False),
        sa.Column(
            "is_priceable",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
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
        sa.PrimaryKeyConstraint("security_key"),
    )
    op.create_index("ix_security_ticker", "security", ["ticker"])
    op.create_index("ix_security_is_priceable", "security", ["is_priceable"])

    op.create_table(
        "security_price",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "security_key",
            sa.String(length=320),
            sa.ForeignKey("security.security_key", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("close", sa.Float(), nullable=False),
        sa.Column("adj_close", sa.Float(), nullable=False),
        sa.Column("volume", sa.BigInteger(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("security_key", "date", name="uq_security_price_security_date"),
    )
    op.create_index("ix_security_price_security_key", "security_price", ["security_key"])
    op.create_index("ix_security_price_date", "security_price", ["date"])
    op.create_index(
        "ix_security_price_security_date",
        "security_price",
        ["security_key", "date"],
    )


def downgrade() -> None:
    op.drop_index("ix_security_price_security_date", table_name="security_price")
    op.drop_index("ix_security_price_date", table_name="security_price")
    op.drop_index("ix_security_price_security_key", table_name="security_price")
    op.drop_table("security_price")
    op.drop_index("ix_security_is_priceable", table_name="security")
    op.drop_index("ix_security_ticker", table_name="security")
    op.drop_table("security")
