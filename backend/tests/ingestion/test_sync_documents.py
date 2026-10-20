from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.models import Base, DocumentRecord
from app.ingestion.sync_documents import DocumentSource, sync_document
from app.retrieval.collections import collection_name, document_point_id
from app.retrieval.qdrant import MemoryVectorIndex


class FakeEmbedder:
    provider = "fake"
    model = "tiny-v1"
    dimension = 2

    def __init__(self):
        self.calls = 0

    def embed(self, texts):
        self.calls += 1
        return [[float(len(text)), 1.0] for text in texts]


def source(content=b"first document"):
    return DocumentSource("manual", "manual.txt", "text/plain", content, "https://example.test/manual")


def test_names_and_ids_are_versioned_and_deterministic():
    assert collection_name("document_chunks", "OpenAI", "text-embedding-3-small", "v1") == "document_chunks_v1_openai_text-embedding-3-small"
    assert document_point_id("manual", "abc", 0) == document_point_id("manual", "abc", 0)


def test_sync_is_incremental_and_replaces_changed_version():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    vectors, embedder = MemoryVectorIndex(), FakeEmbedder()
    with Session(engine) as session:
        first = sync_document(source(), embedder, vectors, session)
        second = sync_document(source(), embedder, vectors, session)
        assert first.changed is True and second.changed is False
        assert embedder.calls == 1
        original_ids = set(vectors.points)
        changed = sync_document(source(b"changed document with more words"), embedder, vectors, session)
        assert changed.changed is True
        assert not original_ids.intersection(vectors.points)
        assert session.scalar(select(DocumentRecord)).version_hash == changed.version_hash


def test_neighbors_are_isolated_by_document_and_version():
    vectors, embedder = MemoryVectorIndex(), FakeEmbedder()
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        result = sync_document(source(b"abcdefghij klmnopqrst uvwxyz"), embedder, vectors, session, max_chars=10, overlap_chars=2)
        middle = vectors.neighbors("manual", result.version_hash, 1, radius=1)
        assert [point.payload["chunk_index"] for point in middle] == [0, 1, 2]
        assert vectors.neighbors("other", result.version_hash, 1, radius=1) == []
