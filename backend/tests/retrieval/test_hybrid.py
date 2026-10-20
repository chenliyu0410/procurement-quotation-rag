from app.retrieval.contextual import ContextualRetriever
from app.retrieval.qdrant import MemoryVectorIndex, VectorPoint
from app.retrieval.schemas import Evidence


def evidence(index, score=1.0):
    return Evidence(id=f"seed-{index}", kind="document", title="手冊", text=f"chunk {index}", source_url="url",
        page_number=1, score=score, metadata={"document_id": "doc", "version_hash": "v1", "chunk_index": index})


def test_context_expansion_keeps_seeds_first_deduplicates_and_caps_at_seven():
    vectors = MemoryVectorIndex(); vectors.collections["docs"] = 2
    for index in range(10):
        point = VectorPoint(str(index), [1, 0], {"collection": "docs", "document_id": "doc", "version_hash": "v1",
            "chunk_index": index, "chunk_text": f"chunk {index}", "document_title": "手冊", "source_url": "url", "page_number": 1})
        vectors.points[point.id] = point
    expanded = ContextualRetriever(vectors).expand([evidence(2), evidence(5), evidence(8)], window=1, final_k=7)
    assert [item.id for item in expanded[:3]] == ["seed-2", "seed-5", "seed-8"]
    assert len(expanded) == 7
    assert len({item.id for item in expanded}) == 7
