import re
from decimal import Decimal

from app.answering.provider import Citation, DraftAnswer
from app.retrieval.schemas import EvidenceBundle


class AnswerValidationError(ValueError):
    pass


def _numbers(text: str) -> set[str]:
    return {format(Decimal(value.replace(",", "")).normalize(), "f")
            for value in re.findall(r"\d[\d,]*(?:\.\d+)?", text)}


def _without_verified_filter_echo(text: str, evidence: EvidenceBundle) -> str:
    """Exclude only explicit, numerically exact statements of SQL filters.

    Filter bounds never enter the evidence number whitelist: a claim about a
    case amount still needs its cited source even when it equals a bound.
    """
    filters = evidence.applied_filters
    if filters is None:
        return text
    label = "預算(?:金額)?" if filters.amount_kind == "budget" else "決標(?:金額)?"
    prefix = rf"(?:篩選條件[:：]?|符合|查詢條件[:：]?)\s*{label}\s*(?:介於|範圍(?:為|在)?|為|在)?\s*"
    number = r"([\d,]+(?:\.\d+)?)\s*(萬|億)?\s*元?\s*"

    def amount(raw, unit):
        return Decimal(raw.replace(",", "")) * {"萬": Decimal(10000), "億": Decimal(100000000)}.get(unit, Decimal(1))

    def complete_clause(match):
        # Inspect the greedy match in the callback to avoid regex backtracking
        # dropping a unit or digit just to satisfy a trailing lookahead.
        before = match.string[:match.start()].rstrip()
        after = match.string[match.end():].lstrip()
        return (not before or before[-1] in "，,。；;：:！？!?\n") and not re.match(
            r"(?:以上|以下|以內|以外|超過|不到|[\d萬億元])", after)

    def range_echo(match):
        left_unit, right_unit = match[2] or match[4], match[4] or match[2]
        return "" if complete_clause(match) and (amount(match[1], left_unit), amount(match[3], right_unit)) == (filters.min_amount, filters.max_amount) else match[0]

    text = re.sub(prefix + number + r"(?:到|至|～|~|－|-)\s*" + number, range_echo, text)

    def bound_echo(match):
        bound = filters.min_amount if match[3] == "以上" else filters.max_amount
        return "" if complete_clause(match) and bound is not None and amount(match[1], match[2]) == bound else match[0]

    return re.sub(prefix + number + r"(以下|以內|以上)", bound_echo, text)


def validate_answer(draft: DraftAnswer, evidence: EvidenceBundle) -> DraftAnswer:
    items = {item.id: item for item in [*evidence.cases, *evidence.documents]}
    citations: list[Citation] = []
    allowed_numbers: set[str] = set()
    cited = {citation.evidence_id for citation in draft.citations}
    for item in (item for key, item in items.items() if key in cited):
        allowed_numbers |= _numbers(item.text)
        allowed_numbers |= _numbers(" ".join(str(value) for value in item.metadata.values() if value is not None))
    for citation in draft.citations:
        item = items.get(citation.evidence_id)
        if item is None:
            raise AnswerValidationError(f"不存在的引用: {citation.evidence_id}")
        citations.append(Citation(evidence_id=item.id, source_url=item.source_url, page_number=item.page_number))
    unsupported = _numbers(_without_verified_filter_echo(draft.answer, evidence)) - allowed_numbers
    if unsupported:
        raise AnswerValidationError(f"回答包含沒有證據支持的金額或數值: {sorted(unsupported)}")
    return DraftAnswer(answer=draft.answer, citations=citations, limitations=draft.limitations)
