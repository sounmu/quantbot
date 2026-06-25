from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class EtfORM(Base):
    __tablename__ = "etf"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticker: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    issuer: Mapped[str] = mapped_column(String(120), index=True)
    theme: Mapped[str | None] = mapped_column(String(120), index=True)
    expense_ratio: Mapped[float | None] = mapped_column(Float)
    inception_date: Mapped[date | None] = mapped_column(Date)
    is_active_etf: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    discloses_daily: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    currency: Mapped[str] = mapped_column(String(8), default="USD", nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    prices: Mapped[list[EtfPriceORM]] = relationship(
        back_populates="etf", cascade="all, delete-orphan"
    )
    holdings: Mapped[list[EtfHoldingORM]] = relationship(
        back_populates="etf", cascade="all, delete-orphan"
    )
    holding_changes: Mapped[list[EtfHoldingChangeORM]] = relationship(
        back_populates="etf", cascade="all, delete-orphan"
    )
    metric: Mapped[EtfMetricORM | None] = relationship(
        back_populates="etf", cascade="all, delete-orphan"
    )


class EtfPriceORM(Base):
    __tablename__ = "etf_price"
    __table_args__ = (UniqueConstraint("etf_id", "date", name="uq_etf_price_etf_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    etf_id: Mapped[int] = mapped_column(ForeignKey("etf.id", ondelete="CASCADE"), index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    open: Mapped[float | None] = mapped_column(Float)
    high: Mapped[float | None] = mapped_column(Float)
    low: Mapped[float | None] = mapped_column(Float)
    close: Mapped[float] = mapped_column(Float)
    nav: Mapped[float | None] = mapped_column(Float)
    volume: Mapped[int | None] = mapped_column(BigInteger)

    etf: Mapped[EtfORM] = relationship(back_populates="prices")


class EtfHoldingORM(Base):
    __tablename__ = "etf_holding"
    __table_args__ = (
        UniqueConstraint(
            "etf_id",
            "as_of_date",
            "holding_key",
            name="uq_etf_holding_snapshot_key",
        ),
        Index("ix_etf_holding_position_key", "etf_id", "holding_key", "as_of_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    etf_id: Mapped[int] = mapped_column(ForeignKey("etf.id", ondelete="CASCADE"), index=True)
    as_of_date: Mapped[date] = mapped_column(Date, index=True)
    holding_key: Mapped[str] = mapped_column(String(320), index=True)
    holding_ticker: Mapped[str | None] = mapped_column(String(32), index=True)
    security_id: Mapped[str | None] = mapped_column(String(64), index=True)
    holding_name: Mapped[str] = mapped_column(String(255))
    weight: Mapped[float] = mapped_column(Float)
    shares: Mapped[float | None] = mapped_column(Float)
    market_value: Mapped[float | None] = mapped_column(Float)

    etf: Mapped[EtfORM] = relationship(back_populates="holdings")


class EtfHoldingChangeORM(Base):
    __tablename__ = "etf_holding_change"
    __table_args__ = (
        UniqueConstraint(
            "etf_id",
            "as_of_date",
            "holding_key",
            name="uq_etf_holding_change_snapshot_key",
        ),
        Index("ix_etf_holding_change_etf_date", "etf_id", "as_of_date"),
        Index("ix_etf_holding_change_position", "etf_id", "holding_key", "as_of_date"),
        Index("ix_etf_holding_change_date", "as_of_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    etf_id: Mapped[int] = mapped_column(ForeignKey("etf.id", ondelete="CASCADE"), index=True)
    as_of_date: Mapped[date] = mapped_column(Date)
    prev_date: Mapped[date | None] = mapped_column(Date)
    holding_key: Mapped[str] = mapped_column(String(320))
    holding_ticker: Mapped[str | None] = mapped_column(String(32))
    security_id: Mapped[str | None] = mapped_column(String(64))
    holding_name: Mapped[str] = mapped_column(String(255))
    change_type: Mapped[str] = mapped_column(String(24))
    shares_before: Mapped[float | None] = mapped_column(Float)
    shares_after: Mapped[float | None] = mapped_column(Float)
    shares_delta: Mapped[float | None] = mapped_column(Float)
    shares_delta_pct: Mapped[float | None] = mapped_column(Float)
    weight_before: Mapped[float | None] = mapped_column(Float)
    weight_after: Mapped[float | None] = mapped_column(Float)
    weight_delta: Mapped[float | None] = mapped_column(Float)

    etf: Mapped[EtfORM] = relationship(back_populates="holding_changes")


class EtfMetricORM(Base):
    __tablename__ = "etf_metric"
    __table_args__ = (UniqueConstraint("etf_id", name="uq_etf_metric_etf_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    etf_id: Mapped[int] = mapped_column(ForeignKey("etf.id", ondelete="CASCADE"), index=True)
    as_of: Mapped[date] = mapped_column(Date)
    aum: Mapped[float | None] = mapped_column(Float)
    return_1m: Mapped[float | None] = mapped_column(Float)
    return_3m: Mapped[float | None] = mapped_column(Float)
    return_ytd: Mapped[float | None] = mapped_column(Float)
    return_1y: Mapped[float | None] = mapped_column(Float)

    etf: Mapped[EtfORM] = relationship(back_populates="metric")


class CollectionRunORM(Base):
    __tablename__ = "collection_run"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_name: Mapped[str] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(32))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    items_processed: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text)


class CollectionItemLogORM(Base):
    __tablename__ = "collection_item_log"
    __table_args__ = (
        Index("ix_collection_item_log_run", "run_id"),
        Index("ix_collection_item_log_etf", "etf_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("collection_run.id", ondelete="CASCADE"))
    etf_id: Mapped[int | None] = mapped_column(ForeignKey("etf.id", ondelete="SET NULL"))
    ticker: Mapped[str] = mapped_column(String(16), index=True)
    item_type: Mapped[str] = mapped_column(String(16))  # "holdings" or "prices"
    status: Mapped[str] = mapped_column(String(16))  # "success" or "failed"
    row_count: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CollectionLockORM(Base):
    __tablename__ = "collection_lock"

    lock_key: Mapped[str] = mapped_column(String(120), primary_key=True)
    acquired_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
