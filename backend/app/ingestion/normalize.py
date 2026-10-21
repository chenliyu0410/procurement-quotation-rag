import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Mapping

from app.ingestion.taxonomy import normalize_category


class NormalizationError(ValueError):
    pass


@dataclass(frozen=True)
class CaseRecord:
    source_dataset: str
    case_number_raw: str | None
    agency: str
    case_name: str
    category_raw: str
    category_normalized: str
    budget_amount: Decimal | None
    award_amount: Decimal | None
    announcement_date: date | None
    expected_tender_date: date | None
    source_period: str
    source_url: str
    source_record_id: str | None = None

    def row_hash(self) -> str:
        payload = json.dumps(asdict(self), ensure_ascii=False, sort_keys=True, default=str)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def parse_money(raw: str | int | Decimal | None) -> Decimal | None:
    if raw is None or str(raw).strip() in {"", "-", "無"}:
        return None
    cleaned = re.sub(r"[^0-9.\-]", "", str(raw).replace(",", ""))
    try:
        return Decimal(cleaned)
    except InvalidOperation as exc:
        raise NormalizationError(f"無法解析金額: {raw}") from exc


def parse_date(raw: str | None, *, month_only: bool = False) -> date | None:
    if not raw or not raw.strip():
        return None
    numbers = [int(value) for value in re.findall(r"\d+", raw)]
    if len(numbers) < 2:
        raise NormalizationError(f"無法解析日期: {raw}")
    year = numbers[0] + 1911 if numbers[0] < 1911 else numbers[0]
    month = numbers[1]
    day = 1 if month_only or len(numbers) < 3 else numbers[2]
    try:
        return date(year, month, day)
    except ValueError as exc:
        raise NormalizationError(f"無法解析日期: {raw}") from exc


def _required(row: Mapping[str, str], source: str, column: str) -> str:
    value = row.get(column)
    if value is None or not str(value).strip():
        raise NormalizationError(f"{source}: 缺少必要欄位 {column}")
    return str(value).strip()


def normalize_work_bureau(row: Mapping[str, str], *, source_period: str = "", source_url: str = "") -> CaseRecord:
    agency = _required(row, "work-bureau", "機關名稱")
    name = _required(row, "work-bureau", "標案名稱")
    category = str(row.get("標的分類", "")).strip()
    announced = parse_date(row.get("決標公告日期"))
    return CaseRecord("work-bureau", (row.get("標案案號") or "").strip() or None, agency, name, category,
        normalize_category(category, name).value, None, parse_money(row.get("總決標金額")), announced, None,
        source_period or (str(announced.year) if announced else ""), source_url)


def normalize_metro_tender(row: Mapping[str, str], *, source_period: str = "", source_url: str = "") -> CaseRecord:
    agency = _required(row, "metro", "主辦單位")
    name = _required(row, "metro", "採購案名")
    category = str(row.get("採購標的", "")).strip()
    expected = parse_date(row.get("預定招標年月"), month_only=True)
    return CaseRecord("metro", (row.get("採購案號") or "").strip() or None, agency, name, category,
        normalize_category(category, name).value, parse_money(row.get("預算金額")), None, None, expected,
        source_period or (expected.strftime("%Y-%m") if expected else ""), source_url)
