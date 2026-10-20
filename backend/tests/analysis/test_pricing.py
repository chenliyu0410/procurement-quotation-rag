from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from app.analysis.pricing import build_price_reference, select_comparables
from app.analysis.schemas import ComparableCase


def case(case_id, amount, year=2024, category="資訊服務", score=1.0, budget=999):
    return SimpleNamespace(id=case_id, award_amount=None if amount is None else Decimal(str(amount)), budget_amount=Decimal(str(budget)),
        announcement_date=date(year, 1, 1), category_normalized=category, score=score)


def test_selects_same_category_recent_unique_positive_top_ten():
    target = SimpleNamespace(category_normalized="資訊服務")
    cases = [case(str(i), i * 100, score=i) for i in range(1, 13)] + [case("old", 100, 2018), case("wrong", 100, category="工程")]
    selected = select_comparables(target, cases, date(2026, 1, 1))
    assert len(selected) == 10
    assert selected[0].case_id == "12"
    assert {item.case_id for item in selected}.isdisjoint({"old", "wrong"})


def test_builds_decimal_quartiles_and_preserves_all_sample_ids():
    values = [ComparableCase(case_id=str(i), award_amount=Decimal(str(value)), similarity_score=float(i))
              for i, value in enumerate([10, 20, 30, 40, 50], 1)]
    result = build_price_reference(values)
    assert (result.q1, result.median, result.q3) == (Decimal("20"), Decimal("30"), Decimal("40"))
    assert result.minimum == Decimal("10") and result.maximum == Decimal("50")
    assert result.case_ids == ["1", "2", "3", "4", "5"]
    assert result.insufficient_sample is False


def test_filters_invalid_and_duplicate_awards_and_reports_insufficient_sample():
    target = SimpleNamespace(category_normalized="資訊服務")
    selected = select_comparables(target, [case("a", 100), case("a", 100), case("zero", 0), case("negative", -1), case("budget-only", None)], date(2026, 1, 1))
    result = build_price_reference(selected)
    assert result.sample_count == 1
    assert result.insufficient_sample is True
    assert result.q1 is result.q3 is None
    assert set(result.exclusions) == {"duplicate", "non_positive_award", "missing_award"}
