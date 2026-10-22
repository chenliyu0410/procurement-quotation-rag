import pytest

from app.answering.service import QueryService
from app.retrieval.schemas import Evidence, EvidenceBundle


@pytest.mark.anyio
@pytest.mark.parametrize("sample_count", [0, 4])
async def test_insufficient_price_samples_cannot_be_replaced_by_model_range(sample_count):
    from app.analysis.schemas import PriceReference
    case = Evidence(id="case:a", kind="case", title="缺少日期的案件", text="決標100元", source_url="https://example.org")

    class Retriever:
        async def retrieve(self, question):
            return EvidenceBundle(cases=[case], price_reference=PriceReference(
                sample_count=sample_count, insufficient_sample=True))

    class Provider:
        async def generate(self, request):
            pytest.fail("Insufficient price samples must not reach generative price answering")

    result = await QueryService(Retriever(), Provider()).query("資訊服務案件的歷史決標金額區間？", [])
    assert "樣本不足" in result["answer"]
    assert result["price_reference"]["sample_count"] == sample_count
    assert result["cases"][0]["id"] == case.id
    assert result["citations"] == []


@pytest.mark.anyio
async def test_price_words_in_document_question_preserve_document_answer():
    from app.analysis.schemas import PriceReference
    from app.answering.provider import Citation, DraftAnswer
    document = Evidence(id="chunk:a", kind="document", title="價格評估程序", text="依程序辦理評估",
                        source_url="https://example.org/procedure.pdf", page_number=1)

    class Retriever:
        async def retrieve(self, question):
            return EvidenceBundle(documents=[document], price_reference=PriceReference(
                sample_count=0, insufficient_sample=True))

    class Provider:
        async def generate(self, request):
            return DraftAnswer(answer="依程序辦理評估", citations=[Citation(evidence_id=document.id)])

    result = await QueryService(Retriever(), Provider()).query("資訊服務採購的價格評估程序", [])
    assert result["answer"] == "依程序辦理評估"
    assert result["citations"][0]["evidence_id"] == document.id
    assert result["citations"][0]["page_number"] == 1


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
