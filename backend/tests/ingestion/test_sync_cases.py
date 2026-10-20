from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.models import Base, DataSource, ProcurementCase, SyncRun
from app.ingestion.normalize import CaseRecord
from app.ingestion.sync_cases import SourceConfig, sync_cases


def record(period: str, amount: str = "100") -> CaseRecord:
    return CaseRecord(source_dataset="demo", case_number_raw="A-1", agency="機關", case_name="資訊設備",
        category_raw="財物", category_normalized="資訊服務", budget_amount=None,
        award_amount=Decimal(amount), announcement_date=date(2024, 1, 1), expected_tender_date=None,
        source_period=period, source_url="https://example.test/data")


def test_sync_is_idempotent_and_newer_period_wins():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        first = sync_cases(SourceConfig("demo", "Demo", "https://example.test", False, "r1", "2024-01", [record("2024-01")]), session)
        second = sync_cases(SourceConfig("demo", "Demo", "https://example.test", False, "r2", "2024-02", [record("2024-02", "150")]), session)
        assert first.changed == second.changed == 1
        cases = session.scalars(select(ProcurementCase)).all()
        assert len(cases) == 1
        assert cases[0].award_amount == Decimal("150.00")
        assert len(session.scalars(select(SyncRun)).all()) == 2


def test_append_source_does_not_delete_missing_historical_rows():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        sync_cases(SourceConfig("demo", "Demo", "https://example.test", False, "r1", "2024-01", [record("2024-01")]), session)
        sync_cases(SourceConfig("demo", "Demo", "https://example.test", False, "r2", "2024-02", []), session)
        assert session.scalar(select(ProcurementCase)).is_active is True


def test_snapshot_source_soft_deletes_missing_rows():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        sync_cases(SourceConfig("demo", "Demo", "https://example.test", True, "r1", "2024-01", [record("2024-01")]), session)
        sync_cases(SourceConfig("demo", "Demo", "https://example.test", True, "r2", "2024-02", []), session)
        assert session.scalar(select(ProcurementCase)).is_active is False
