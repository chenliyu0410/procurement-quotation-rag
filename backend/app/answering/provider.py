from typing import Protocol

from pydantic import BaseModel, Field

from app.analysis.schemas import PriceReference
from app.retrieval.schemas import EvidenceBundle


class Citation(BaseModel):
    evidence_id: str
    source_url: str | None = None
    page_number: int | None = None


class DraftAnswer(BaseModel):
    answer: str
    citations: list[Citation] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class GroundedAnswerRequest(BaseModel):
    question: str
    evidence: EvidenceBundle
    price_reference: PriceReference | None = None


class AnswerProvider(Protocol):
    async def generate(self, request: GroundedAnswerRequest) -> DraftAnswer: ...
