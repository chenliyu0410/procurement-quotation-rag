from dataclasses import dataclass
from typing import Any, Protocol, Sequence

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

    def neighbors(self, document_id: str, version_hash: str, chunk_index: int, radius: int = 1) -> list[VectorPoint]:
        return sorted((point for point in self.points.values()
                       if point.payload.get("document_id") == document_id
                       and point.payload.get("version_hash") == version_hash
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

    def switch_alias(self, alias: str, collection: str) -> None:
        operations: list[Any] = []
        aliases = {item.alias_name for item in self.client.get_aliases().aliases}
        if alias in aliases:
            operations.append(models.DeleteAliasOperation(delete_alias=models.DeleteAlias(alias_name=alias)))
        operations.append(models.CreateAliasOperation(create_alias=models.CreateAlias(collection_name=collection, alias_name=alias)))
        self.client.update_collection_aliases(operations)
