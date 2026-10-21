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
