import hashlib
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import DocumentRecord
from app.ingestion.pdf import PageText, chunk_pages, extract_pages
from app.retrieval.collections import collection_name, document_point_id
from app.retrieval.embeddings import EmbeddingProvider
from app.retrieval.qdrant import VectorIndex, VectorPoint


@dataclass(frozen=True)
class DocumentSource:
    document_id: str
    filename: str
    content_type: str
    content: bytes
    source_url: str


@dataclass(frozen=True)
class DocumentSyncSummary:
    changed: bool
    version_hash: str
    chunk_count: int
    collection: str


def _pages(source: DocumentSource) -> list[PageText]:
    if source.content_type == "application/pdf":
        return extract_pages(source.content)
    return [PageText(1, source.content.decode("utf-8"))]


def sync_document(source: DocumentSource, embedder: EmbeddingProvider, vectors: VectorIndex, session: Session,
                  max_chars: int = 500, overlap_chars: int = 80) -> DocumentSyncSummary:
    version_hash = hashlib.sha256(source.content).hexdigest()
    settings = get_settings()
    collection = collection_name("document_chunks", embedder.provider, embedder.model, settings.index_schema_version)
    current = session.get(DocumentRecord, source.document_id)
    if current and current.version_hash == version_hash and current.collection_name == collection:
        return DocumentSyncSummary(False, version_hash, current.chunk_count, collection)

    chunks = chunk_pages(_pages(source), max_chars, overlap_chars)
    embeddings = embedder.embed([chunk.text for chunk in chunks]) if chunks else []
    vectors.ensure_collection(collection, embedder.dimension)
    if current:
        vectors.delete_document(current.collection_name, source.document_id)
    points = [VectorPoint(str(document_point_id(source.document_id, version_hash, chunk.chunk_index)), vector, {
        "collection": collection, "document_id": source.document_id, "version_hash": version_hash,
        "document_title": source.filename, "source_url": source.source_url, "page_number": chunk.page_number,
        "chunk_index": chunk.chunk_index, "chunk_text": chunk.text,
    }) for chunk, vector in zip(chunks, embeddings, strict=True)]
    vectors.upsert(collection, points)
    if current is None:
        current = DocumentRecord(id=source.document_id, source=source.source_url, filename=source.filename,
            content_type=source.content_type, content_size=len(source.content), version_hash=version_hash,
            chunk_count=len(chunks), embedding_provider=embedder.provider, embedding_model=embedder.model,
            collection_name=collection)
        session.add(current)
    else:
        current.source, current.filename, current.content_type = source.source_url, source.filename, source.content_type
        current.content_size, current.version_hash, current.chunk_count = len(source.content), version_hash, len(chunks)
        current.embedding_provider, current.embedding_model, current.collection_name = embedder.provider, embedder.model, collection
    session.commit()
    return DocumentSyncSummary(True, version_hash, len(chunks), collection)
