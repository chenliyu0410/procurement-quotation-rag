import pytest

from app.answering.service import QueryService
from app.retrieval.schemas import Evidence, EvidenceBundle


@pytest.mark.anyio
async def test_generation_timeout_preserves_retrieved_cases():
    case = Evidence(id="case:one", kind="case", title="資訊服務", text="決標100元",
                    source_url="https://example.org/case", case_id="one")

    class Retriever:
        async def retrieve(self, question):
            return EvidenceBundle(cases=[case])

    class Provider:
        async def generate(self, request):
            raise TimeoutError

    result = await QueryService(Retriever(), Provider()).query("找資訊服務", [])
    assert result["cases"][0]["id"] == case.id
    assert result["sync_metadata"]["status"] == "partial"
    assert result["limitations"]


@pytest.mark.anyio
async def test_invalid_model_answer_preserves_cases_without_exposing_draft():
    from app.answering.provider import DraftAnswer, Citation
    case = Evidence(id="case:a", kind="case", title="A", text="決標100元", source_url="https://example.org")

    class Retriever:
        async def retrieve(self, question):
            return EvidenceBundle(cases=[case])

    class Provider:
        async def generate(self, request):
            return DraftAnswer(answer="決標999元", citations=[Citation(evidence_id=case.id)])

    result = await QueryService(Retriever(), Provider()).query("金額", [])
    assert result["sync_metadata"]["status"] == "partial"
    assert len(result["cases"]) == 1
    assert "999" not in result["answer"]
