from dataclasses import dataclass
from typing import Any, Protocol, Sequence
import math

from qdrant_client import QdrantClient
from qdrant_client.http import models


@dataclass(frozen=True)
class VectorPoint:
    id: str
    vector: list[float]
    payload: dict[str, Any]


class VectorIndex(Protocol):
    def ensure_collection(self, name: str, dimension: int) -> None: ...
    def upsert(self, collection: str, points: Sequence[VectorPoint]) -> None: ...
    def delete_document(self, collection: str, document_id: str) -> None: ...
    def delete_case(self, collection: str, case_id: str) -> None: ...
    def search(self, collection: str, vector: list[float], filters: dict[str, Any], limit: int): ...
    def neighbors(self, document_id: str, version_hash: str, chunk_index: int, radius: int = 1, collection: str | None = None) -> list[VectorPoint]: ...


class MemoryVectorIndex:
    def __init__(self) -> None:
        self.collections: dict[str, int] = {}
        self.points: dict[str, VectorPoint] = {}

    def ensure_collection(self, name: str, dimension: int) -> None:
        existing = self.collections.get(name)
        if existing is not None and existing != dimension:
            raise ValueError(f"collection {name} has dimension {existing}, requested {dimension}")
        self.collections[name] = dimension

    def upsert(self, collection: str, points: Sequence[VectorPoint]) -> None:
        for point in points:
            self.points[point.id] = point

    def delete_document(self, collection: str, document_id: str) -> None:
        self.points = {key: value for key, value in self.points.items()
                       if not (value.payload.get("collection") == collection and value.payload.get("document_id") == document_id)}

    def delete_case(self, collection: str, case_id: str) -> None:
        self.points = {key: value for key, value in self.points.items()
                       if not (value.payload.get("collection") == collection and value.payload.get("case_id") == case_id)}

    def search(self, collection: str, vector: list[float], filters: dict[str, Any], limit: int) -> list[tuple[VectorPoint, float]]:
        def cosine(candidate: list[float]) -> float:
            dot = sum(a * b for a, b in zip(vector, candidate, strict=True))
            norm = math.sqrt(sum(a * a for a in vector)) * math.sqrt(sum(b * b for b in candidate))
            return dot / norm if norm else 0.0
        matches = [(point, cosine(point.vector)) for point in self.points.values()
                   if point.payload.get("collection") == collection
                   and all(point.payload.get(key) == value for key, value in filters.items())]
        return sorted(matches, key=lambda item: (-item[1], item[0].id))[:limit]

    def neighbors(self, document_id: str, version_hash: str, chunk_index: int, radius: int = 1, collection: str | None = None) -> list[VectorPoint]:
        return sorted((point for point in self.points.values()
                       if point.payload.get("document_id") == document_id
                       and point.payload.get("version_hash") == version_hash
                       and (collection is None or point.payload.get("collection") == collection)
                       and abs(int(point.payload["chunk_index"]) - chunk_index) <= radius),
                      key=lambda point: int(point.payload["chunk_index"]))


class QdrantVectorIndex:
    def __init__(self, client: QdrantClient) -> None:
        self.client = client

    def ensure_collection(self, name: str, dimension: int) -> None:
        if not self.client.collection_exists(name):
            self.client.create_collection(name, vectors_config=models.VectorParams(size=dimension, distance=models.Distance.COSINE))
            return
        config = self.client.get_collection(name).config.params.vectors
        existing = config.size if hasattr(config, "size") else None
        if existing is not None and existing != dimension:
            raise ValueError(f"collection {name} has dimension {existing}, requested {dimension}")

    def upsert(self, collection: str, points: Sequence[VectorPoint]) -> None:
        self.client.upsert(collection, [models.PointStruct(id=point.id, vector=point.vector, payload=point.payload) for point in points], wait=True)

    def delete_document(self, collection: str, document_id: str) -> None:
        if not self.client.collection_exists(collection):
            return
        selector = models.FilterSelector(filter=models.Filter(must=[
            models.FieldCondition(key="document_id", match=models.MatchValue(value=document_id))
        ]))
        self.client.delete(collection, selector, wait=True)

    def delete_case(self, collection: str, case_id: str) -> None:
        if not self.client.collection_exists(collection):
            return
        selector = models.FilterSelector(filter=models.Filter(must=[models.FieldCondition(key="case_id", match=models.MatchValue(value=case_id))]))
        self.client.delete(collection, selector, wait=True)

    def search(self, collection: str, vector: list[float], filters: dict[str, Any], limit: int):
        if not self.client.collection_exists(collection):
            return []
        query_filter = models.Filter(must=[models.FieldCondition(key=key, match=models.MatchValue(value=value)) for key, value in filters.items()]) if filters else None
        response = self.client.query_points(collection, query=vector, query_filter=query_filter, limit=limit, with_payload=True)
        return [(VectorPoint(str(point.id), [], dict(point.payload or {})), float(point.score)) for point in response.points]

    def neighbors(self, document_id: str, version_hash: str, chunk_index: int, radius: int = 1, collection: str | None = None) -> list[VectorPoint]:
        if collection is None:
            raise ValueError("Qdrant neighbor lookup requires a collection")
        conditions = [
            models.FieldCondition(key="document_id", match=models.MatchValue(value=document_id)),
            models.FieldCondition(key="version_hash", match=models.MatchValue(value=version_hash)),
            models.FieldCondition(key="chunk_index", range=models.Range(gte=chunk_index - radius, lte=chunk_index + radius)),
        ]
        records, _ = self.client.scroll(collection, scroll_filter=models.Filter(must=conditions), limit=radius * 2 + 1, with_payload=True)
        points = [VectorPoint(str(record.id), [], dict(record.payload or {})) for record in records]
        return sorted(points, key=lambda point: int(point.payload["chunk_index"]))

    def switch_alias(self, alias: str, collection: str) -> None:
        operations: list[Any] = []
        aliases = {item.alias_name for item in self.client.get_aliases().aliases}
        if alias in aliases:
            operations.append(models.DeleteAliasOperation(delete_alias=models.DeleteAlias(alias_name=alias)))
        operations.append(models.CreateAliasOperation(create_alias=models.CreateAlias(collection_name=collection, alias_name=alias)))
        self.client.update_collection_aliases(operations)
