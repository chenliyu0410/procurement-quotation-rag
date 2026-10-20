import re
import uuid


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9_-]+", "-", value.casefold()).strip("-")


def collection_name(kind: str, provider: str, model: str, index_version: str) -> str:
    return "_".join((_slug(kind), _slug(index_version), _slug(provider), _slug(model)))


def document_point_id(document_id: str, version_hash: str, chunk_index: int) -> uuid.UUID:
    return uuid.uuid5(uuid.NAMESPACE_URL, f"document:{document_id}:{version_hash}:{chunk_index}")
