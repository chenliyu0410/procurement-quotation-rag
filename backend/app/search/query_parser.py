import calendar
import re
from datetime import date
from decimal import Decimal

from pydantic import ValidationError

from app.search.schemas import CaseFilters


class QueryParseError(ValueError):
    pass


_DIGITS = {"零": 0, "一": 1, "二": 2, "兩": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}


def _number(raw: str) -> Decimal:
    raw = raw.strip().replace(",", "")
    if raw in _DIGITS:
        return Decimal(_DIGITS[raw])
    return Decimal(raw)


def _amount(raw: str, unit: str) -> Decimal:
    multiplier = Decimal("10000") if unit == "萬" else Decimal("100000000") if unit == "億" else Decimal(1)
    return _number(raw) * multiplier


class QueryParser:
    def parse(self, question: str) -> CaseFilters:
        values: dict[str, object] = {"amount_kind": "budget" if "預算" in question else "award"}
        range_match = re.search(r"([\d,.]+|[零一二兩三四五六七八九十]+)\s*(萬|億)?\s*(?:到|至|～|~)\s*([\d,.]+|[零一二兩三四五六七八九十]+)\s*(萬|億)?", question)
        if range_match:
            left_unit, right_unit = range_match.group(2) or range_match.group(4) or "", range_match.group(4) or range_match.group(2) or ""
            values["min_amount"] = _amount(range_match.group(1), left_unit)
            values["max_amount"] = _amount(range_match.group(3), right_unit)
        else:
            bound = re.search(r"([\d,.]+|[零一二兩三四五六七八九十]+)\s*(萬|億)?\s*(以下|以內|以上)", question)
            if bound:
                values["max_amount" if bound.group(3) in ("以下", "以內") else "min_amount"] = _amount(bound.group(1), bound.group(2) or "")

        dates = re.search(r"(?:民國)?(\d{2,4})年(\d{1,2})月\s*(?:到|至|～|~)?\s*(?:(\d{1,2})月)?", question)
        if dates:
            year = int(dates.group(1)); year = year + 1911 if year < 1911 else year
            start_month, end_month = int(dates.group(2)), int(dates.group(3) or dates.group(2))
            values["start_date"] = date(year, start_month, 1)
            values["end_date"] = date(year, end_month, calendar.monthrange(year, end_month)[1])

        for category in ("資訊服務", "工程", "財物", "勞務", "其他"):
            if category in question:
                values["category"] = category
                break
        agency = re.search(r"([\u4e00-\u9fff]{2,20}(?:局|處|公司|機關))", question)
        if agency:
            values["agency"] = agency.group(1).removeprefix("找")
        try:
            return CaseFilters.model_validate(values)
        except (ValidationError, ValueError) as exc:
            message = "；".join(error["msg"].removeprefix("Value error, ") for error in exc.errors()) if isinstance(exc, ValidationError) else str(exc)
            raise QueryParseError(message) from exc
