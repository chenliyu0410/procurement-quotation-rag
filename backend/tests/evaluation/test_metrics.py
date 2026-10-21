from app.evaluation.run import calculate_metrics
import pytest


def test_metrics_and_latency_p95_are_deterministic():
    rows = [{"structured_correct": True, "citations_valid": True, "recall_at_5": 1, "grounded": True, "refusal_correct": True, "latency_ms": value} for value in (10, 20, 30, 40, 100)]
    result = calculate_metrics(rows)
    assert result["structured_accuracy"] == 1.0
    assert result["citation_validity"] == 1.0
    assert result["recall_at_5"] == 1.0
    assert result["groundedness"] == 1.0
    assert result["refusal_accuracy"] == 1.0
    assert result["latency_p95_ms"] == 88.0


def test_unreviewed_questions_have_no_fabricated_scores_or_latency():
    result = calculate_metrics([{"id": "one", "question": "找採購案件"}])
    assert all(value is None for value in result.values())


def test_mixed_outcomes_and_missing_annotations():
    result = calculate_metrics([
        {"structured_correct": True, "recall_at_5": .5, "latency_ms": 20},
        {"structured_correct": False, "recall_at_5": 1, "latency_ms": 40},
        {"structured_correct": None, "latency_ms": None},
    ])
    assert result["structured_accuracy"] == .5
    assert result["recall_at_5"] == .75
    assert result["groundedness"] is None
    assert result["latency_p95_ms"] == 39


@pytest.mark.parametrize("row", [
    {"recall_at_5": 1.1}, {"latency_ms": -1},
    {"grounded": "true"}, {"latency_ms": float("nan")},
])
def test_rejects_invalid_measurements(row):
    with pytest.raises(ValueError):
        calculate_metrics([row])
