import argparse
from dataclasses import replace
from pathlib import Path
from sqlalchemy import select

from qdrant_client import QdrantClient

from app.config import get_settings
from app.db.session import build_session_factory
from app.db.models import ProcurementCase
from app.retrieval.sync_case_vectors import sync_case_vectors
from app.ingestion.data_taipei import fetch_api, parse_csv
from app.ingestion.http import download
from app.ingestion.normalize import normalize_metro_tender, normalize_work_bureau
from app.ingestion.sync_cases import SourceConfig, sync_cases
from app.ingestion.sync_documents import DocumentSource, sync_document
from app.retrieval.embeddings import OpenAIEmbeddingProvider
from app.retrieval.qdrant import QdrantVectorIndex


SOURCES = {
    "work-bureau": ("臺北市政府工務局採購案件", normalize_work_bureau, False),
    "metro": ("臺北捷運公司採購案件預定招標時程", normalize_metro_tender, False),
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Procurement data administration")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("sync-case-vectors", help="Index all active cases and remove inactive vectors")
    sync = commands.add_parser("sync-cases")
    sync.add_argument("--source", required=True, choices=("work-bureau", "metro"))
    sync.add_argument("--resource-url", required=True)
    sync.add_argument("--period", required=True)
    sync.add_argument("--format", choices=("csv", "api"), default="csv")
    sync.add_argument("--dry-run", action="store_true", help="Download and normalize without database writes")
    documents = commands.add_parser("sync-documents")
    documents.add_argument("path", type=Path)
    documents.add_argument("--document-id", required=True)
    documents.add_argument("--source-url", required=True)
    documents.add_argument("--dimension", type=int, default=1536)
    args = parser.parse_args()
    if args.command == "sync-case-vectors":
        settings = get_settings()
        if not settings.llm_api_key or not settings.embedding_model:
            parser.error("LLM_API_KEY and EMBEDDING_MODEL are required for sync-case-vectors")
        embedder = OpenAIEmbeddingProvider(settings.llm_api_key, settings.embedding_model,
                                           settings.embedding_dimension, settings.llm_base_url)
        vectors = QdrantVectorIndex(QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key or None))
        with build_session_factory()() as session:
            result = sync_case_vectors(session.scalars(select(ProcurementCase)).all(), embedder, vectors, settings.index_schema_version)
        print(f"案件向量同步完成: upserted={result.upserted}, deleted={result.deleted}, collection={result.collection}")
        return
    if args.command == "sync-documents":
        settings = get_settings()
        if not settings.llm_api_key or not settings.embedding_model:
            parser.error("LLM_API_KEY and EMBEDDING_MODEL are required for sync-documents")
        content = args.path.read_bytes()
        mime = "application/pdf" if args.path.suffix.casefold() == ".pdf" else "text/plain"
        embedder = OpenAIEmbeddingProvider(settings.llm_api_key, settings.embedding_model, args.dimension, settings.llm_base_url)
        vectors = QdrantVectorIndex(QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key or None))
        with build_session_factory()() as session:
            result = sync_document(DocumentSource(args.document_id, args.path.name, mime, content, args.source_url), embedder, vectors, session)
        print(f"文件同步完成: changed={result.changed}, chunks={result.chunk_count}, collection={result.collection}")
        return
    name, normalizer, snapshot_mode = SOURCES[args.source]
    if args.format == "api":
        snapshot = fetch_api(args.resource_url)
        checksum, resource_id = snapshot.checksum, snapshot.resource_id
        records = [replace(normalizer(row, source_period=args.period, source_url=args.resource_url),
                           source_record_id=f"{resource_id}:{row['_id']}") for row in snapshot.rows]
    else:
        content, checksum = download(args.resource_url)
        records = parse_csv(content, normalizer, source_period=args.period, source_url=args.resource_url)
        resource_id = args.resource_url.rstrip("/").split("/")[-2] if "/resource/" in args.resource_url else checksum[:12]
    if args.dry_run:
        print(f"Dry run: records={len(records)}, resource_id={resource_id}, "
              f"missing_award_dates={sum(item.announcement_date is None for item in records)}")
        return
    factory = build_session_factory()
    with factory() as session:
        summary = sync_cases(SourceConfig(args.source, name, args.resource_url, snapshot_mode, resource_id,
            args.period, records, checksum), session)
    print(f"同步完成: seen={summary.seen}, changed={summary.changed}, deactivated={summary.deactivated}")


if __name__ == "__main__":
    main()
