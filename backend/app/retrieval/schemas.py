from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field
from app.analysis.schemas import PriceReference
from app.search.schemas import CaseFilters


class QueryIntent(StrEnum):
    CASES = "cases"
    DOCUMENTS = "documents"
    COMBINED = "combined"


class Evidence(BaseModel):
    id: str
    kind: str
    title: str
    text: str
    source_url: str
    page_number: int | None = None
    case_id: str | None = None
    score: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvidenceBundle(BaseModel):
    cases: list[Evidence] = Field(default_factory=list)
    documents: list[Evidence] = Field(default_factory=list)
    price_reference: PriceReference | None = None
    applied_filters: CaseFilters | None = None
