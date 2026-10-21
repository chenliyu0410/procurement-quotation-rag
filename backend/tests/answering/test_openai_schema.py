import json

import httpx
import pytest

from app.answering.openai import OpenAIAnswerProvider
from app.answering.provider import GroundedAnswerRequest
from app.config import Settings
from app.retrieval.schemas import Evidence, EvidenceBundle


@pytest.mark.anyio
async def test_model_can_only_emit_complete_current_evidence_ids():
    def handler(request):
        body = json.loads(request.content)
        schema = body["text"]["format"]["schema"]
        citation_id = schema["properties"]["citations"]["items"]["properties"]["evidence_id"]
        assert citation_id["enum"] == ["case:abc"]
        return httpx.Response(200, json={"status": "completed", "output": [{"type": "message", "content": [
            {"type": "output_text", "text": '{"answer":"檢修案","citations":[{"evidence_id":"case:abc"}],"limitations":[]}'}]}]})

    evidence = EvidenceBundle(cases=[Evidence(id="case:abc", kind="case", title="檢修案", text="檢修案",
                               source_url="https://example.org", case_id="abc", metadata={"id": "abc"})])
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        answer = await OpenAIAnswerProvider(Settings(llm_api_key="test", llm_model="test-model"), client).generate(
            GroundedAnswerRequest(question="相似案件", evidence=evidence))
    assert answer.citations[0].evidence_id == "case:abc"
