from decimal import Decimal

from pydantic import BaseModel, Field


class ComparableCase(BaseModel):
    case_id: str
    award_amount: Decimal
    similarity_score: float


class PriceReference(BaseModel):
    sample_count: int
    minimum: Decimal | None = None
    q1: Decimal | None = None
    median: Decimal | None = None
    q3: Decimal | None = None
    maximum: Decimal | None = None
    insufficient_sample: bool
    case_ids: list[str] = Field(default_factory=list)
    exclusions: dict[str, int] = Field(default_factory=dict)
