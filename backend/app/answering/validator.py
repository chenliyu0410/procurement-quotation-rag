import re

from app.answering.provider import Citation, DraftAnswer
from app.retrieval.schemas import EvidenceBundle


class AnswerValidationError(ValueError):
    pass


def _numbers(text: str) -> set[str]:
    return {value.replace(",", "") for value in re.findall(r"\d[\d,]*(?:\.\d+)?", text)}


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
    unsupported = _numbers(draft.answer) - allowed_numbers
    if unsupported:
        raise AnswerValidationError(f"回答包含沒有證據支持的金額或數值: {sorted(unsupported)}")
    return DraftAnswer(answer=draft.answer, citations=citations, limitations=draft.limitations)
