from typing import Any, Protocol, Sequence
import httpx

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
        partial_price = evidence.price_reference.model_dump(mode="json") if evidence.price_reference else None
        try:
            draft = await self.provider.generate(GroundedAnswerRequest(question=rewritten.standalone_question, evidence=evidence,
                                                                       price_reference=evidence.price_reference))
            answer = validate_answer(draft, evidence)
        except TimeoutError:
            return {"answer": "模型暫時無法完成文字說明，以下為已取得的案件。",
                    "cases": [item.model_dump(mode="json") for item in evidence.cases],
                    "price_reference": partial_price, "citations": [],
                    "limitations": ["模型回應逾時，請稍後重試。"],
                    "sync_metadata": {"status": "partial"}}
        except (httpx.HTTPError, ValueError):
            return {"answer": "文字回答未通過驗證或模型暫時無法使用，請參閱已查得的案件與統計。",
                    "cases": [item.model_dump(mode="json") for item in evidence.cases],
                    "price_reference": partial_price, "citations": [],
                    "limitations": ["請稍後重試；目前僅顯示檢索結果。"], "sync_metadata": {"status": "partial"}}
        return {"answer": answer.answer, "cases": [item.model_dump(mode="json") for item in evidence.cases],
                "price_reference": evidence.price_reference.model_dump(mode="json") if evidence.price_reference else None, "citations": [item.model_dump(mode="json") for item in answer.citations],
                "limitations": answer.limitations, "sync_metadata": {"status": "ready"}}
