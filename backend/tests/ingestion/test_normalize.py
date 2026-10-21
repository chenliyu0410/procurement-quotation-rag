from decimal import Decimal
from pathlib import Path

import pytest

from app.ingestion.normalize import NormalizationError, normalize_metro_tender, normalize_work_bureau, parse_money
from app.ingestion.data_taipei import parse_csv
from app.ingestion.taxonomy import normalize_category


def test_parse_money_handles_commas_currency_and_empty_values():
    assert parse_money("NT$ 3,500,000元") == Decimal("3500000")
    assert parse_money(1200) == Decimal("1200")
    assert parse_money("") is None
    assert parse_money(None) is None


def test_normalize_work_bureau_supports_roc_and_iso_dates():
    case = normalize_work_bureau({
        "機關名稱": "臺北市政府工務局", "標案案號": "WB-001", "標案名稱": "道路改善工程",
        "標的分類": "工程類", "總決標金額": "3,500,000", "決標公告日期": "113/08/15",
    })
    assert case.award_amount == Decimal("3500000")
    assert case.announcement_date.isoformat() == "2024-08-15"
    assert case.category_normalized == "工程"


def test_normalize_metro_tender_supports_roc_month():
    case = normalize_metro_tender({
        "主辦單位": "臺北大眾捷運股份有限公司", "採購案號": "MRT-001", "採購案名": "車站網路設備更新",
        "採購標的": "財物類", "預算金額": "12,000,000", "預定招標年月": "113年10月",
    })
    assert case.budget_amount == Decimal("12000000")
    assert case.expected_tender_date.isoformat() == "2024-10-01"
    assert case.category_normalized == "資訊服務"


def test_missing_or_renamed_required_column_is_diagnostic():
    with pytest.raises(NormalizationError, match="work-bureau.*標案名稱"):
        normalize_work_bureau({"機關名稱": "工務局", "案件名稱": "欄名已變更"})


def test_taxonomy_is_fixed_and_unknown_falls_back_to_other():
    assert normalize_category("勞務類", "清潔服務").value == "勞務"
    assert normalize_category("未分類", "無法識別項目").value == "其他"


def test_fixed_csv_fixtures_are_parsed():
    fixtures = Path(__file__).parents[1] / "fixtures"
    work = parse_csv((fixtures / "work_bureau.csv").read_bytes(), normalize_work_bureau,
                     source_period="2024", source_url="https://example.test/work")
    metro = parse_csv((fixtures / "metro_tenders.csv").read_bytes(), normalize_metro_tender,
                      source_period="2024-10", source_url="https://example.test/metro")
    assert len(work) == 2
    assert len(metro) == 1


def test_official_metro_schema_preserves_reporting_month_without_inventing_tender_date():
    row = {"序號/編號": "1", "標案名稱": "捷運廠站空調系統設備檢修工作", "預算金額": "7,599,391",
           "標的分類": "勞務類", "統計期_民國年月": "11510"}
    record = normalize_metro_tender(row, source_period="2026-10")
    assert record.agency == "臺北大眾捷運股份有限公司"
    assert record.case_number_raw is None
    assert record.budget_amount == Decimal("7599391")
    assert record.source_period == "2026-10"
    assert record.expected_tender_date is record.announcement_date is record.award_amount is None


def test_official_metro_unpublished_budget_is_null():
    row = {"序號/編號": "3", "標案名稱": "空壓機電纜線軍規接頭等2項採購", "預算金額": "預算金額不公開",
           "標的分類": "財物類", "統計期_民國年月": "11510"}
    assert normalize_metro_tender(row).budget_amount is None


def test_official_metro_reporting_period_must_match_requested_snapshot():
    row = {"標案名稱": "捷運設備", "預算金額": "100", "標的分類": "財物類", "統計期_民國年月": "11510"}
    with pytest.raises(NormalizationError, match="期別"):
        normalize_metro_tender(row, source_period="2026-09")
