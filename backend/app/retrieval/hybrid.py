from app.retrieval.contextual import ContextualRetriever
from app.retrieval.embeddings import EmbeddingProvider
from app.retrieval.schemas import EvidenceBundle, QueryIntent
from app.retrieval.vector_repository import VectorRepository
from app.search.schemas import CaseFilters


class HybridRetriever:
    def __init__(self, embedder: EmbeddingProvider, repository: VectorRepository, contextual: ContextualRetriever) -> None:
        self.embedder, self.repository, self.contextual = embedder, repository, contextual

    def retrieve(self, question: str, filters: CaseFilters, intent: QueryIntent) -> EvidenceBundle:
        vector = self.embedder.embed([question])[0]
        metadata = {"category_normalized": filters.category} if filters.category else {}
        cases = self.repository.search_cases(vector, metadata) if intent in (QueryIntent.CASES, QueryIntent.COMBINED) else []
        seeds = self.repository.search_chunks(vector, {}, 3) if intent in (QueryIntent.DOCUMENTS, QueryIntent.COMBINED) else []
        return EvidenceBundle(cases=cases, documents=self.contextual.expand(seeds) if seeds else [])
