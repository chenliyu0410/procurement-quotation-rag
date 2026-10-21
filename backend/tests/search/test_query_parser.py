from decimal import Decimal

import pytest

from app.search.query_parser import QueryParseError, QueryParser


def test_parses_million_range_and_amount_kind():
    value = QueryParser().parse("找預算 300 萬到 500 萬的資訊服務案件")
    assert value.min_amount == Decimal("3000000")
    assert value.max_amount == Decimal("5000000")
    assert value.amount_kind == "budget"
    assert value.category == "資訊服務"


def test_parses_one_hundred_million_upper_bound():
    value = QueryParser().parse("決標金額一億以下")
    assert value.min_amount is None
    assert value.max_amount == Decimal("100000000")
    assert value.amount_kind == "award"


def test_parses_roc_month_range_with_inclusive_end():
    value = QueryParser().parse("民國113年1月至6月的案件")
    assert value.start_date.isoformat() == "2024-01-01"
    assert value.end_date.isoformat() == "2024-06-30"


def test_rejects_reversed_amount_range():
    with pytest.raises(QueryParseError, match="下限不得大於上限"):
        QueryParser().parse("500萬到300萬")


def test_question_without_amount_has_empty_bounds():
    value = QueryParser().parse("找工務局的工程案件")
    assert value.min_amount is value.max_amount is None
    assert value.agency == "工務局"


def test_full_year_and_agency_after_year():
    value = QueryParser().parse("找民國113年工務局的工程案件")
    assert value.start_date.isoformat() == "2024-01-01"
    assert value.end_date.isoformat() == "2024-12-31"
    assert value.agency == "工務局"


def test_money_range_allows_yuan_on_both_sides():
    value = QueryParser().parse("找預算300萬元到500萬元的資訊設備案件")
    assert value.min_amount == 3000000
    assert value.max_amount == 5000000
    assert value.category == "資訊服務"


def test_quoted_case_title_does_not_turn_title_year_into_date_filter():
    value = QueryParser().parse("找與「114年度續約-臺北市積水預警預報工作」相似的案件")
    assert value.start_date is value.end_date is None


def test_explicit_filters_outside_quoted_title_are_preserved():
    value = QueryParser().parse("找民國113年與「114年度設備300萬元採購案」相似，預算500萬以下的案件")
    assert value.start_date.isoformat() == "2024-01-01"
    assert value.end_date.isoformat() == "2024-12-31"
    assert value.max_amount == 5000000


@pytest.mark.parametrize("question,field,expected", [
    ("找「工務局」決標500萬以下的案件", "agency", "工務局"),
    ("找分類為「資訊服務」的案件", "category", "資訊服務"),
    ("找預算「300萬到500萬」的案件", "min_amount", Decimal("3000000")),
])
def test_quoted_hard_conditions_are_not_discarded(question, field, expected):
    assert getattr(QueryParser().parse(question), field) == expected
