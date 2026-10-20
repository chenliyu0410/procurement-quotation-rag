import pytest

from app.answering.provider import Citation, DraftAnswer
from app.answering.query_rewriter import ChatTurn, QueryRewriter
from app.answering.validator import AnswerValidationError, validate_answer
from app.retrieval.schemas import Evidence, EvidenceBundle


def bundle():
    item = Evidence(id="case:a", kind="case", title="案件 A", text="決標金額 100 元", source_url="url", case_id="a",
        metadata={"award_amount": "100"})
    return EvidenceBundle(cases=[item])


def test_rewriter_keeps_original_and_only_last_two_turns():
    history = [ChatTurn(role="user", content=str(i)) for i in range(4)]
    rewritten = QueryRewriter(lambda q, h: f"{h[0].content}-{h[-1].content}-{q}").rewrite("那金額呢？", history)
    assert rewritten.original_question == "那金額呢？"
    assert rewritten.standalone_question == "2-3-那金額呢？"


def test_validator_rejects_unknown_citation_and_changed_amount():
    with pytest.raises(AnswerValidationError, match="不存在的引用"):
        validate_answer(DraftAnswer(answer="無", citations=[Citation(evidence_id="missing")]), bundle())
    with pytest.raises(AnswerValidationError, match="金額"):
        validate_answer(DraftAnswer(answer="決標金額為 200 元", citations=[Citation(evidence_id="case:a")]), bundle())


def test_validator_accepts_grounded_answer():
    result = validate_answer(DraftAnswer(answer="決標金額為 100 元", citations=[Citation(evidence_id="case:a")]), bundle())
    assert result.citations[0].source_url == "url"
