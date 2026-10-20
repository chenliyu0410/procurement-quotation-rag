import hashlib
import uuid
from dataclasses import dataclass
from typing import Iterable, Any

from app.retrieval.collections import collection_name
from app.retrieval.embeddings import EmbeddingProvider
from app.retrieval.qdrant import VectorIndex, VectorPoint


@dataclass(frozen=True)
class CaseVectorSyncSummary:
    collection: str
    upserted: int
    deleted: int


def _point_id(case_id: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"procurement-case:{case_id}"))


def sync_case_vectors(cases: Iterable[Any], embedder: EmbeddingProvider, vectors: VectorIndex, index_version: str) -> CaseVectorSyncSummary:
    collection = collection_name("procurement_cases", embedder.provider, embedder.model, index_version)
    vectors.ensure_collection(collection, embedder.dimension)
    active, deleted = [], 0
    for case in cases:
        if not case.is_active:
            vectors.delete_case(collection, case.id)
            deleted += 1
        else:
            active.append(case)
    texts = [f"{case.case_name} {case.agency} {case.category_normalized}" for case in active]
    embeddings = embedder.embed(texts) if texts else []
    points = []
    for case, text, vector in zip(active, texts, embeddings, strict=True):
        payload = {"collection": collection, "case_id": case.id, "title": case.case_name, "text": text,
            "agency": case.agency, "category_normalized": case.category_normalized, "source_url": case.source_url,
            "budget_amount": str(case.budget_amount) if case.budget_amount is not None else None,
            "award_amount": str(case.award_amount) if case.award_amount is not None else None,
            "content_hash": hashlib.sha256(text.encode()).hexdigest()}
        points.append(VectorPoint(_point_id(case.id), vector, payload))
    vectors.upsert(collection, points)
    return CaseVectorSyncSummary(collection, len(points), deleted)
