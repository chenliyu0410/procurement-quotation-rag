from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.config import Settings
from app.db.identity import build_case_identity
from app.db.models import Base, DocumentRecord, ProcurementCase


def test_settings_expose_qdrant_and_index_configuration(monkeypatch):
    monkeypatch.setenv("QDRANT_URL", "http://vector.test:6333")
    monkeypatch.setenv("QDRANT_API_KEY", "secret")
    monkeypatch.setenv("EMBEDDING_PROVIDER", "openai")
    monkeypatch.setenv("INDEX_SCHEMA_VERSION", "v2")

    settings = Settings(_env_file=None)

    assert settings.qdrant_url == "http://vector.test:6333"
    assert settings.qdrant_api_key == "secret"
    assert settings.embedding_provider == "openai"
    assert settings.index_schema_version == "v2"


def test_case_identity_prefers_official_number_and_isolates_datasets():
    first = build_case_identity("work-bureau", " A-001 ", "工務局", "測試案", 2025)
    renamed = build_case_identity("work-bureau", "a-001", "不同機關", "不同名稱", 2026)
    other_dataset = build_case_identity("metro", "a-001", "工務局", "測試案", 2025)

    assert first == renamed
    assert first != other_dataset


def test_case_identity_without_number_uses_agency_name_and_year():
    first = build_case_identity("metro", None, "臺北捷運公司", "資訊系統維護", 2026)
    same = build_case_identity("metro", "", " 臺北捷運公司 ", "資訊系統  維護", 2026)
    next_year = build_case_identity("metro", None, "臺北捷運公司", "資訊系統維護", 2027)

    assert first == same
    assert first != next_year


def test_models_store_procurement_and_document_registry_fields():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    case = ProcurementCase(
        id="case-1",
        source_dataset="work-bureau",
        case_number_raw="A-001",
        agency="工務局",
        case_name="資訊服務案",
        category_raw="勞務類",
        category_normalized="資訊服務",
        budget_amount=None,
        award_amount=Decimal("1234567.89"),
        source_period="2025",
        source_row_hash="row-hash",
        is_active=True,
        source_url="https://data.taipei/example",
        ingested_at=datetime.now(timezone.utc),
    )
    document = DocumentRecord(
        id="doc-1",
        source="data.taipei",
        filename="manual.pdf",
        content_type="application/pdf",
        content_size=1234,
        version_hash="sha256",
        chunk_count=8,
        embedding_provider="openai",
        embedding_model="text-embedding-test",
        collection_name="document_chunks_v1_openai_test",
        indexed_at=datetime.now(timezone.utc),
    )

    with Session(engine) as session:
        session.add_all([case, document])
        session.commit()
        loaded_case = session.get(ProcurementCase, "case-1")
        loaded_document = session.get(DocumentRecord, "doc-1")

    assert loaded_case is not None
    assert loaded_case.award_amount == Decimal("1234567.89")
    assert loaded_case.category_raw == "勞務類"
    assert loaded_case.category_normalized == "資訊服務"
    assert loaded_document is not None
    assert loaded_document.chunk_count == 8
    assert loaded_document.collection_name == "document_chunks_v1_openai_test"
