from typing import Any

from app.retrieval.qdrant import VectorIndex
from app.retrieval.schemas import Evidence


class VectorRepository:
    def __init__(self, vectors: VectorIndex, case_collection: str, document_collection: str) -> None:
        self.vectors, self.case_collection, self.document_collection = vectors, case_collection, document_collection

    def search_cases(self, query_vector: list[float], filters: dict[str, Any], limit: int = 10) -> list[Evidence]:
        found = self.vectors.search(self.case_collection, query_vector, filters, limit)
        return [Evidence(id=f"case:{point.payload['case_id']}", kind="case", title=point.payload["title"], text=point.payload["text"],
            source_url=point.payload["source_url"], case_id=point.payload["case_id"], score=score, metadata=point.payload) for point, score in found]

    def search_chunks(self, query_vector: list[float], filters: dict[str, Any], limit: int = 3) -> list[Evidence]:
        found = self.vectors.search(self.document_collection, query_vector, filters, limit)
        return [Evidence(id=f"chunk:{point.id}", kind="document", title=point.payload["document_title"], text=point.payload["chunk_text"],
            source_url=point.payload["source_url"], page_number=point.payload.get("page_number"), score=score, metadata=point.payload) for point, score in found]
