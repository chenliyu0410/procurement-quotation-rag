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


def test_default_rewriter_retains_filter_context_for_followup():
    rewritten = QueryRewriter().rewrite("那其中最低呢？", [ChatTurn(role="user", content="資訊服務預算300萬到500萬")])
    assert "資訊服務預算300萬到500萬" in rewritten.standalone_question


def test_validator_rejects_unknown_citation_and_changed_amount():
    with pytest.raises(AnswerValidationError, match="不存在的引用"):
        validate_answer(DraftAnswer(answer="無", citations=[Citation(evidence_id="missing")]), bundle())
    with pytest.raises(AnswerValidationError, match="金額"):
        validate_answer(DraftAnswer(answer="決標金額為 200 元", citations=[Citation(evidence_id="case:a")]), bundle())


def test_validator_accepts_grounded_answer():
    result = validate_answer(DraftAnswer(answer="決標金額為 100 元", citations=[Citation(evidence_id="case:a")]), bundle())
    assert result.citations[0].source_url == "url"


def test_amount_must_be_supported_by_cited_evidence():
    evidence = bundle()
    evidence.cases.append(Evidence(id="case:b", kind="case", title="B", text="決標200元", source_url="url"))
    with pytest.raises(AnswerValidationError):
        validate_answer(DraftAnswer(answer="A決標200元", citations=[Citation(evidence_id="case:a")]), evidence)


def test_equivalent_decimal_money_formats_are_accepted():
    evidence = EvidenceBundle(cases=[Evidence(id="case:a", kind="case", title="檢修案",
        text="決標金額216300.00元", source_url="https://example.org", metadata={"award_amount": "216300.00"})])
    draft = DraftAnswer(answer="決標金額216,300元", citations=[Citation(evidence_id="case:a")])
    assert validate_answer(draft, evidence).answer == draft.answer


def test_verified_budget_filter_echo_is_not_mistaken_for_a_case_amount():
    from app.search.schemas import CaseFilters
    evidence = EvidenceBundle(cases=[Evidence(id="case:a", kind="case", title="設備案", text="預算7599391.00元",
        source_url="https://example.org")], applied_filters=CaseFilters(amount_kind="budget", min_amount=3000000, max_amount=10000000))
    draft = DraftAnswer(answer="符合預算介於300萬到1000萬元之案件，預算7599391元。", citations=[Citation(evidence_id="case:a")])
    assert validate_answer(draft, evidence).answer == draft.answer


@pytest.mark.parametrize("answer", [
    "本案預算3000000元。", "符合預算300萬到2000萬元的案件。",
    "本案不符合預算300萬到1000萬元。", "符合預算300萬到1000萬元以上。",
    "未符合預算300萬到1000萬元。", "符合預算300萬到1000萬元以下。",
])
def test_filter_bounds_cannot_authorize_invented_case_amounts_or_changed_ranges(answer):
    from app.search.schemas import CaseFilters
    evidence = EvidenceBundle(cases=[Evidence(id="case:a", kind="case", title="設備案", text="預算7599391.00元",
        source_url="https://example.org")], applied_filters=CaseFilters(amount_kind="budget", min_amount=3000000, max_amount=10000000))
    with pytest.raises(AnswerValidationError):
        validate_answer(DraftAnswer(answer=answer, citations=[Citation(evidence_id="case:a")]), evidence)


def test_verified_upper_bound_echo_and_unverified_amount_remain_distinct():
    from app.search.schemas import CaseFilters
    evidence = EvidenceBundle(cases=[Evidence(id="case:a", kind="case", title="設備案", text="預算7599391元",
        source_url="https://example.org")], applied_filters=CaseFilters(amount_kind="budget", max_amount=10000000))
    valid = DraftAnswer(answer="篩選條件：預算1000萬以下，設備案預算7599391元。", citations=[Citation(evidence_id="case:a")])
    assert validate_answer(valid, evidence).answer == valid.answer
    with pytest.raises(AnswerValidationError):
        validate_answer(valid.model_copy(update={"answer": "篩選條件：預算1000萬以下，設備案預算10000000元。"}), evidence)
