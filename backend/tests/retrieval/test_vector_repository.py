from types import SimpleNamespace

from app.retrieval.qdrant import MemoryVectorIndex
from app.retrieval.sync_case_vectors import sync_case_vectors
from app.retrieval.vector_repository import VectorRepository


class Embedder:
    provider, model, dimension = "fake", "v1", 2
    def embed(self, texts): return [[float("資訊" in text), 1.0] for text in texts]


def case(case_id="case-a", name="資訊系統", active=True):
    return SimpleNamespace(id=case_id, case_name=name, agency="工務局", category_normalized="資訊服務",
        budget_amount=100, award_amount=90, announcement_date=None, expected_tender_date=None,
        source_url="https://example.test", is_active=active)


def test_case_sync_uses_separate_versioned_collection_and_stable_upsert():
    vectors, embedder = MemoryVectorIndex(), Embedder()
    first = sync_case_vectors([case()], embedder, vectors, "v1")
    ids = set(vectors.points)
    second = sync_case_vectors([case(name="資訊系統更新")], embedder, vectors, "v1")
    assert first.collection.startswith("procurement_cases_v1_")
    assert set(vectors.points) == ids
    assert second.upserted == 1
    sync_case_vectors([case(active=False)], embedder, vectors, "v1")
    assert vectors.points == {}


def test_vector_repository_applies_metadata_filter_limit_and_order():
    vectors, embedder = MemoryVectorIndex(), Embedder()
    result = sync_case_vectors([case("a"), SimpleNamespace(**{**case("b").__dict__, "category_normalized": "工程", "case_name": "道路"})], embedder, vectors, "v1")
    found = VectorRepository(vectors, result.collection, "unused").search_cases([1.0, 1.0], {"category_normalized": "資訊服務"}, 1)
    assert [item.case_id for item in found] == ["a"]
