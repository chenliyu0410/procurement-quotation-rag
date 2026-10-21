"""Composition root for the persisted SQL, vector, pricing and model services."""

from datetime import datetime
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import anyio
from qdrant_client import QdrantClient

from app.analysis.pricing import build_price_reference, select_comparables
from app.answering.openai import OpenAIAnswerProvider
from app.answering.service import QueryService
from app.config import Settings
from app.db.session import build_session_factory
from app.retrieval.collections import collection_name
from app.retrieval.contextual import ContextualRetriever
from app.retrieval.embeddings import OpenAIEmbeddingProvider
from app.retrieval.qdrant import QdrantVectorIndex
from app.retrieval.schemas import Evidence, EvidenceBundle
from app.retrieval.vector_repository import VectorRepository
from app.search.case_repository import CaseRepository
from app.search.query_parser import QueryParser


class RuntimeRetriever:
    def __init__(self, sessions, embedder, vectors, index_version):
        self.sessions, self.embedder, self.vectors = sessions, embedder, vectors
        self.repository = VectorRepository(vectors,
            collection_name("procurement_cases", embedder.provider, embedder.model, index_version),
            collection_name("document_chunks", embedder.provider, embedder.model, index_version))

    async def retrieve(self, question: str) -> EvidenceBundle:
        return await anyio.to_thread.run_sync(self._retrieve, question)

    def _retrieve(self, question: str) -> EvidenceBundle:
        filters = QueryParser().parse(question)
        pricing = any(word in question for word in ("區間", "歷史金額", "報價", "價格"))
        documents = any(word in question for word in ("手冊", "程序", "規範", "招決標方式", "同質", "異質"))
        semantic = pricing or documents or any(word in question for word in ("相似", "類似"))
        selected = []
        chunks = []
        scores = {}
        if semantic:
            vector = self.embedder.embed([question])[0]
            if not documents:
                metadata = {"category_normalized": filters.category} if filters.category else {}
                ranked = self.repository.search_cases(vector, metadata, limit=200)
                scores = {item.case_id: item.score for item in ranked}
                with self.sessions() as session:
                    rows = CaseRepository(session).search(filters, limit=200, case_ids=list(scores))
                selected = sorted((row for row in rows if row.id in scores), key=lambda row: (-scores[row.id], row.id))
            else:
                selected = []
                seeds = self.repository.search_chunks(vector, {}, limit=3)
                chunks = ContextualRetriever(self.vectors).expand(seeds) if seeds else []
        else:
            with self.sessions() as session:
                selected = CaseRepository(session).search(filters, limit=200)
        price = None
        if pricing and filters.category:
            candidates = [SimpleNamespace(**{**row.model_dump(), "category_normalized": row.category,
                           "score": scores.get(row.id, 0.)}) for row in selected]
            now = datetime.now(ZoneInfo("Asia/Taipei")).date()
            price = build_price_reference(select_comparables(SimpleNamespace(category_normalized=filters.category), candidates, now))
            if price.case_ids:
                selected = [row for row in selected if row.id in price.case_ids]
        cases = []
        for row in selected[:10 if semantic else 50]:
            metadata = {**row.model_dump(mode="json"), "category_normalized": row.category}
            cases.append(Evidence(id=f"case:{row.id}", kind="case", title=row.case_name,
                text=f"{row.case_name}；機關：{row.agency}；預算：{row.budget_amount}；決標：{row.award_amount}",
                case_id=row.id, source_url=row.source_url, score=scores.get(row.id, 0.), metadata=metadata))
        return EvidenceBundle(cases=cases, documents=chunks, price_reference=price)


def build_query_service(settings: Settings):
    if not (settings.llm_api_key and settings.llm_model and settings.embedding_model):
        return None
    if settings.embedding_provider != "openai":
        raise ValueError("Only the openai embedding provider is currently supported")
    embedder = OpenAIEmbeddingProvider(settings.llm_api_key, settings.embedding_model,
                                       settings.embedding_dimension, settings.llm_base_url)
    vectors = QdrantVectorIndex(QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key or None, check_compatibility=False))
    retriever = RuntimeRetriever(build_session_factory(settings.database_url), embedder, vectors, settings.index_schema_version)
    return QueryService(retriever, OpenAIAnswerProvider(settings))
