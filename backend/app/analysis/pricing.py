from collections import Counter
from datetime import date
from decimal import Decimal
from typing import Any, Sequence

from app.analysis.schemas import ComparableCase, PriceReference


class ComparableSelection(list[ComparableCase]):
    def __init__(self, values=(), exclusions=None):
        super().__init__(values)
        self.exclusions = dict(exclusions or {})


def select_comparables(target: Any, cases: Sequence[Any], now: date, limit: int = 10, years: int = 5) -> list[ComparableCase]:
    cutoff = now.replace(year=now.year - years)
    exclusions: Counter[str] = Counter()
    seen: set[str] = set()
    selected: list[ComparableCase] = []
    for case in sorted(cases, key=lambda item: (-float(getattr(item, "score", 0.0)), str(item.id))):
        if case.category_normalized != target.category_normalized:
            exclusions["category_mismatch"] += 1
            continue
        if not case.announcement_date or case.announcement_date < cutoff or case.announcement_date > now:
            exclusions["outside_date_window"] += 1
            continue
        if case.id in seen:
            exclusions["duplicate"] += 1
            continue
        seen.add(case.id)
        if case.award_amount is None:
            exclusions["missing_award"] += 1
            continue
        amount = Decimal(case.award_amount)
        if amount <= 0:
            exclusions["non_positive_award"] += 1
            continue
        selected.append(ComparableCase(case_id=case.id, award_amount=amount, similarity_score=float(getattr(case, "score", 0.0))))
        if len(selected) >= limit:
            break
    return ComparableSelection(selected, exclusions)


def _percentile(values: list[Decimal], percentile: Decimal) -> Decimal:
    if len(values) == 1:
        return values[0]
    position = Decimal(len(values) - 1) * percentile
    lower = int(position)
    fraction = position - lower
    if fraction == 0:
        return values[lower]
    return values[lower] + (values[lower + 1] - values[lower]) * fraction


def build_price_reference(cases: Sequence[ComparableCase]) -> PriceReference:
    values = sorted(case.award_amount for case in cases)
    insufficient = len(values) < 5
    return PriceReference(sample_count=len(values), minimum=values[0] if values else None,
        q1=None if insufficient else _percentile(values, Decimal("0.25")),
        median=_percentile(values, Decimal("0.5")) if values else None,
        q3=None if insufficient else _percentile(values, Decimal("0.75")), maximum=values[-1] if values else None,
        insufficient_sample=insufficient, case_ids=[case.case_id for case in cases],
        exclusions=getattr(cases, "exclusions", {}))
