from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from app.answering.query_rewriter import ChatTurn


class QueryRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    history: list[ChatTurn] = Field(default_factory=list, max_length=2)


router = APIRouter(prefix="/api")


@router.post("/query")
async def query(payload: QueryRequest, request: Request) -> dict[str, Any]:
    try:
        return await request.app.state.query_service.query(payload.question, payload.history)
    except TimeoutError:
        return {"answer": "模型暫時無法完成文字說明。", "cases": [], "price_reference": None, "citations": [],
                "limitations": ["模型回應逾時，請稍後重試。"], "sync_metadata": {"status": "ready"}}
