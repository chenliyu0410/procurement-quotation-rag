from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class DataSource(Base):
    __tablename__ = "data_sources"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    dataset_url: Mapped[str] = mapped_column(Text)
    snapshot_mode: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ProcurementCase(Base):
    __tablename__ = "procurement_cases"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    source_dataset: Mapped[str] = mapped_column(String(100), index=True)
    case_number_raw: Mapped[str | None] = mapped_column(String(255), nullable=True)
    agency: Mapped[str] = mapped_column(String(255), index=True)
    case_name: Mapped[str] = mapped_column(Text)
    category_raw: Mapped[str] = mapped_column(String(255), default="")
    category_normalized: Mapped[str] = mapped_column(String(50), index=True)
    budget_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    award_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    announcement_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    expected_tender_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    source_period: Mapped[str] = mapped_column(String(20), default="")
    source_row_hash: Mapped[str] = mapped_column(String(64))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    source_url: Mapped[str] = mapped_column(Text)
    source_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class DocumentRecord(Base):
    __tablename__ = "document_records"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    source: Mapped[str] = mapped_column(Text)
    filename: Mapped[str] = mapped_column(String(500))
    content_type: Mapped[str] = mapped_column(String(100))
    content_size: Mapped[int] = mapped_column(Integer)
    version_hash: Mapped[str] = mapped_column(String(64))
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    embedding_provider: Mapped[str] = mapped_column(String(100))
    embedding_model: Mapped[str] = mapped_column(String(255))
    collection_name: Mapped[str] = mapped_column(String(255))
    indexed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class SyncRun(Base):
    __tablename__ = "sync_runs"
    __table_args__ = (UniqueConstraint("source_id", "started_at", name="uq_sync_source_started"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_id: Mapped[str] = mapped_column(ForeignKey("data_sources.id"), index=True)
    status: Mapped[str] = mapped_column(String(30))
    resource_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_period: Mapped[str] = mapped_column(String(20), default="")
    checksum: Mapped[str | None] = mapped_column(String(64), nullable=True)
    records_seen: Mapped[int] = mapped_column(Integer, default=0)
    records_changed: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
