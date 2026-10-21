from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator


class CaseFilters(BaseModel):
    agency: str | None = None
    category: str | None = None
    min_amount: Decimal | None = None
    max_amount: Decimal | None = None
    start_date: date | None = None
    end_date: date | None = None
    amount_kind: Literal["budget", "award"] = "award"

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_ranges(self):
        if self.min_amount is not None and self.max_amount is not None and self.min_amount > self.max_amount:
            raise ValueError("金額下限不得大於上限")
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValueError("日期下限不得大於上限")
        return self


class CaseResult(BaseModel):
    id: str
    agency: str
    case_name: str
    category: str
    budget_amount: Decimal | None
    award_amount: Decimal | None
    announcement_date: date | None
    expected_tender_date: date | None
    source_url: str
    source_period: str = ""
