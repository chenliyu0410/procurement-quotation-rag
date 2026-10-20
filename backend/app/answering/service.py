from typing import Any, Protocol, Sequence

from app.answering.provider import AnswerProvider, GroundedAnswerRequest
from app.answering.query_rewriter import ChatTurn, QueryRewriter
from app.answering.validator import validate_answer
from app.retrieval.schemas import EvidenceBundle


class RetrievalService(Protocol):
    async def retrieve(self, question: str) -> EvidenceBundle: ...


class QueryService:
    def __init__(self, retriever: RetrievalService, provider: AnswerProvider, rewriter: QueryRewriter | None = None) -> None:
        self.retriever, self.provider, self.rewriter = retriever, provider, rewriter or QueryRewriter()

    async def query(self, question: str, history: Sequence[ChatTurn]) -> dict[str, Any]:
        rewritten = self.rewriter.rewrite(question, history)
        evidence = await self.retriever.retrieve(rewritten.standalone_question)
        if not evidence.cases and not evidence.documents:
            return {"answer": "目前資料中找不到足夠證據回答這個問題。", "cases": [], "price_reference": None,
                    "citations": [], "limitations": ["沒有可引用的案件或文件。"], "sync_metadata": {"status": "ready"}}
        draft = await self.provider.generate(GroundedAnswerRequest(question=rewritten.standalone_question, evidence=evidence))
        answer = validate_answer(draft, evidence)
        return {"answer": answer.answer, "cases": [item.model_dump(mode="json") for item in evidence.cases],
                "price_reference": None, "citations": [item.model_dump(mode="json") for item in answer.citations],
                "limitations": answer.limitations, "sync_metadata": {"status": "ready"}}
