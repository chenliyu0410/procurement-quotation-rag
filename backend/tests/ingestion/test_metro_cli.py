import sys
from types import SimpleNamespace

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app import cli
from app.db.models import Base, ProcurementCase


def test_metro_api_rows_keep_case_identity_across_monthly_resource_ids(monkeypatch):
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(engine)
    monkeypatch.setattr(cli, "build_session_factory", lambda: sessions)
    for month, row_id in (("10", 1), ("11", 99)):
        row = {"_id": row_id, "標案名稱": "捷運設備維護", "標的分類": "勞務類", "預算金額": "1000",
               "統計期_民國年月": f"115{month}"}
        monkeypatch.setattr(cli, "fetch_api", lambda url, row=row, month=month:
                            SimpleNamespace(rows=[row], checksum="snapshot-" + month, resource_id="resource-" + month))
        monkeypatch.setattr(sys, "argv", ["cli", "sync-cases", "--source", "metro", "--format", "api",
                            "--resource-url", "https://data.taipei/test", "--period", "2026-" + month])
        cli.main()
    with sessions() as session:
        cases = session.scalars(select(ProcurementCase)).all()
        assert len(cases) == 1
        assert cases[0].source_period == "2026-11"
        assert cases[0].source_record_id is None


def test_vector_sync_can_limit_embedding_to_new_source(monkeypatch):
    from app.retrieval.qdrant import MemoryVectorIndex
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(engine)
    with sessions() as session:
        for source in ("work-bureau", "metro"):
            session.add(ProcurementCase(id=source, source_dataset=source, agency="機關", case_name="設備維護",
                category_normalized="資訊服務", source_row_hash=source, source_url="https://example.org"))
        session.commit()
    vectors = MemoryVectorIndex()

    class Embedder:
        provider, model, dimension = "fake", "test", 2

        def embed(self, texts):
            assert len(texts) == 1
            return [[1., 0.]]

    monkeypatch.setattr(cli, "get_settings", lambda: SimpleNamespace(llm_api_key="test", embedding_model="test",
        embedding_dimension=2, llm_base_url="https://example.org", qdrant_url="http://localhost", qdrant_api_key="", index_schema_version="v1"))
    monkeypatch.setattr(cli, "OpenAIEmbeddingProvider", lambda *args: Embedder())
    monkeypatch.setattr(cli, "QdrantClient", lambda **kwargs: None)
    monkeypatch.setattr(cli, "QdrantVectorIndex", lambda client: vectors)
    monkeypatch.setattr(cli, "build_session_factory", lambda: sessions)
    monkeypatch.setattr(sys, "argv", ["cli", "sync-case-vectors", "--source", "metro"])
    cli.main()
    assert [point.payload["case_id"] for point in vectors.points.values()] == ["metro"]
