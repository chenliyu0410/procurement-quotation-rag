from datetime import date

import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.answering.provider import DraftAnswer, GroundedAnswerRequest
from app.config import Settings
from app.db.models import Base, ProcurementCase
from app.main import create_app
from app.retrieval.qdrant import MemoryVectorIndex
from app.retrieval.schemas import EvidenceBundle


def database():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine)
    with factory() as session:
        for i in range(6):
            session.add(ProcurementCase(id=str(i), source_dataset="fixture", agency="工務局",
                case_name=f"資訊服務{i}", category_normalized="資訊服務", budget_amount=4000000,
                award_amount=100 + i, announcement_date=date(2026, 1, 1), source_row_hash=str(i),
                expected_tender_date=date(2026, 1, 1), source_url="https://example.org/case"))
        session.commit()
    return factory


class Embedder:
    provider, model, dimension = "fake", "test", 2

    def embed(self, texts):
        return [[1., 0.] for _ in texts]


@pytest.mark.anyio
async def test_runtime_wires_sql_vectors_pricing_and_query_endpoint(client_factory):
    from app.runtime import RuntimeRetriever
    from app.answering.service import QueryService
    from app.retrieval.sync_case_vectors import sync_case_vectors
    from sqlalchemy import select

    factory, vectors = database(), MemoryVectorIndex()
    with factory() as session:
        sync_case_vectors(session.scalars(select(ProcurementCase)).all(), Embedder(), vectors, "v1")
    retriever = RuntimeRetriever(factory, Embedder(), vectors, "v1")

    class Provider:
        async def generate(self, request):
            return DraftAnswer(answer="已找到案件，請參閱案件表與統計。")

    async with client_factory(create_app(QueryService(retriever, Provider()))) as client:
        response = await client.post("/api/query", json={"question": "資訊服務歷史決標金額區間"})
        filtered = await client.post("/api/query", json={"question": "預算500萬到600萬的資訊服務案件"})
    assert response.status_code == 200
    assert len(response.json()["cases"]) == 6
    assert response.json()["price_reference"]["sample_count"] == 6
    from decimal import Decimal
    assert Decimal(response.json()["price_reference"]["q1"]) == Decimal("101.25")
    assert filtered.json()["cases"] == []


@pytest.mark.anyio
async def test_openai_provider_parses_structured_output_without_network():
    from app.answering.openai import OpenAIAnswerProvider

    def handler(request):
        import json
        body = json.loads(request.content)
        assert body["model"] == "configured-model"
        assert body["text"]["format"]["type"] == "json_schema"
        assert body["store"] is False
        return httpx.Response(200, json={"status": "completed", "output": [{"type": "message", "content": [
            {"type": "output_text", "text": '{"answer":"資料不足","citations":[],"limitations":[]}'}]}]})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = OpenAIAnswerProvider(Settings(llm_api_key="test", llm_model="configured-model"), client)
        answer = await provider.generate(GroundedAnswerRequest(question="查詢", evidence=EvidenceBundle()))
    assert answer.answer == "資料不足"


def test_configured_factory_installs_runtime_service():
    from app.runtime import build_query_service
    from app.answering.service import QueryService

    assert isinstance(build_query_service(Settings(llm_api_key="test", llm_model="configured-model",
                       embedding_model="configured-embedding")), QueryService)
