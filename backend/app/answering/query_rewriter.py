from collections.abc import Callable, Sequence

from pydantic import BaseModel


class ChatTurn(BaseModel):
    role: str
    content: str


class RewrittenQuery(BaseModel):
    original_question: str
    standalone_question: str


class QueryRewriter:
    def __init__(self, rewrite_fn: Callable[[str, Sequence[ChatTurn]], str] | None = None) -> None:
        self.rewrite_fn = rewrite_fn

    def rewrite(self, question: str, history: Sequence[ChatTurn]) -> RewrittenQuery:
        recent = list(history[-2:])
        standalone = self.rewrite_fn(question, recent) if self.rewrite_fn and recent else question
        return RewrittenQuery(original_question=question, standalone_question=standalone)
