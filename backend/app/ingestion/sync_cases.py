import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.identity import build_case_identity
from app.db.models import DataSource, ProcurementCase, SyncRun
from app.ingestion.normalize import CaseRecord


@dataclass(frozen=True)
class SourceConfig:
    source_id: str
    name: str
    dataset_url: str
    snapshot_mode: bool
    resource_id: str
    source_period: str
    records: Iterable[CaseRecord]
    checksum: str | None = None


@dataclass(frozen=True)
class SyncSummary:
    seen: int
    changed: int
    deactivated: int


def _period_year(record: CaseRecord) -> int:
    if record.expected_tender_date:
        return record.expected_tender_date.year
    if record.announcement_date:
        return record.announcement_date.year
    digits = "".join(char for char in record.source_period if char.isdigit())
    return int(digits[:4]) if len(digits) >= 4 else 0


def sync_cases(source: SourceConfig, session: Session) -> SyncSummary:
    started = datetime.now(timezone.utc)
    data_source = session.get(DataSource, source.source_id)
    if data_source is None:
        data_source = DataSource(id=source.source_id, name=source.name, dataset_url=source.dataset_url, snapshot_mode=source.snapshot_mode)
        session.add(data_source)
    else:
        data_source.name, data_source.dataset_url, data_source.snapshot_mode = source.name, source.dataset_url, source.snapshot_mode

    records = list(source.records)
    checksum = source.checksum or hashlib.sha256("".join(item.row_hash() for item in records).encode()).hexdigest()
    run = SyncRun(source_id=source.source_id, status="running", resource_id=source.resource_id,
        source_period=source.source_period, checksum=checksum, started_at=started)
    session.add(run)
    session.flush()
    seen_ids: set[str] = set()
    changed = 0
    try:
        for record in records:
            case_id = build_case_identity(record.source_dataset, record.case_number_raw, record.agency, record.case_name,
                                          _period_year(record), record.source_record_id)
            seen_ids.add(case_id)
            current = session.get(ProcurementCase, case_id)
            if current is not None and current.source_period > record.source_period:
                continue
            row_hash = record.row_hash()
            if current is None:
                current = ProcurementCase(id=case_id, source_dataset=record.source_dataset, source_row_hash=row_hash,
                    agency=record.agency, case_name=record.case_name, category_normalized=record.category_normalized,
                    source_url=record.source_url)
                session.add(current)
            if current.source_row_hash != row_hash or not current.is_active:
                changed += 1
            for field in ("source_record_id", "case_number_raw", "agency", "case_name", "category_raw", "category_normalized",
                          "budget_amount", "award_amount", "announcement_date", "expected_tender_date", "source_period", "source_url"):
                setattr(current, field, getattr(record, field))
            current.source_row_hash, current.is_active, current.ingested_at = row_hash, True, started

        deactivated = 0
        if source.snapshot_mode:
            active = session.scalars(select(ProcurementCase).where(ProcurementCase.source_dataset == source.source_id, ProcurementCase.is_active.is_(True))).all()
            for case in active:
                if case.id not in seen_ids:
                    case.is_active = False
                    deactivated += 1
        run.status, run.records_seen, run.records_changed = "success", len(records), changed + deactivated
        run.completed_at = datetime.now(timezone.utc)
        session.commit()
        return SyncSummary(len(records), changed, deactivated)
    except Exception as exc:
        session.rollback()
        failed = SyncRun(source_id=source.source_id, status="failed", resource_id=source.resource_id,
            source_period=source.source_period, checksum=checksum, error_message=str(exc), started_at=started,
            completed_at=datetime.now(timezone.utc))
        session.add(failed)
        session.commit()
        raise
