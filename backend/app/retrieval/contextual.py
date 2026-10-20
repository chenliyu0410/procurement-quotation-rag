from app.retrieval.qdrant import VectorIndex
from app.retrieval.schemas import Evidence


class ContextualRetriever:
    def __init__(self, vectors: VectorIndex) -> None:
        self.vectors = vectors

    def expand(self, seeds: list[Evidence], window: int = 1, final_k: int = 7) -> list[Evidence]:
        result = list(seeds[:final_k])
        seen = {(item.metadata.get("document_id"), item.metadata.get("version_hash"), item.metadata.get("chunk_index")) for item in result}
        for seed in seeds:
            metadata = seed.metadata
            neighbors = self.vectors.neighbors(metadata["document_id"], metadata["version_hash"],
                int(metadata["chunk_index"]), window, metadata.get("collection"))
            neighbors.sort(key=lambda point: (abs(int(point.payload["chunk_index"]) - int(metadata["chunk_index"])), int(point.payload["chunk_index"])))
            for point in neighbors:
                key = (point.payload["document_id"], point.payload["version_hash"], point.payload["chunk_index"])
                if key in seen:
                    continue
                seen.add(key)
                result.append(Evidence(id=f"chunk:{point.id}", kind="document", title=point.payload["document_title"],
                    text=point.payload["chunk_text"], source_url=point.payload["source_url"],
                    page_number=point.payload.get("page_number"), score=seed.score, metadata=point.payload))
                if len(result) >= final_k:
                    return result
        return result
