import argparse
import json
import math
from pathlib import Path


RATE_FIELDS = {
    "structured_accuracy": "structured_correct", "citation_validity": "citations_valid",
    "recall_at_5": "recall_at_5", "groundedness": "grounded", "refusal_accuracy": "refusal_correct",
}


def _validate(rows):
    for row in rows:
        for key in RATE_FIELDS.values():
            value = row.get(key)
            if value is None:
                continue
            if key == "recall_at_5":
                if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 1:
                    raise ValueError(f"{key} must be a finite number between 0 and 1")
            elif type(value) is not bool:
                raise ValueError(f"{key} must be a boolean or null")
        latency = row.get("latency_ms")
        if latency is not None and (type(latency) not in (int, float) or not math.isfinite(latency) or latency < 0):
            raise ValueError("latency_ms must be a finite non-negative number")


def _rate(rows, key):
    values = [float(row[key]) for row in rows if row.get(key) is not None]
    return sum(values) / len(values) if values else None


def _percentile(values, percentile):
    ordered = sorted(float(value) for value in values)
    if not ordered: return None
    position = (len(ordered) - 1) * percentile; lower = int(position); fraction = position - lower
    value = ordered[lower] if fraction == 0 else ordered[lower] + (ordered[lower + 1] - ordered[lower]) * fraction
    return round(value, 6)


def calculate_metrics(rows):
    _validate(rows)
    return {"structured_accuracy": _rate(rows, "structured_correct"), "citation_validity": _rate(rows, "citations_valid"),
        "recall_at_5": _rate(rows, "recall_at_5"), "groundedness": _rate(rows, "grounded"),
        "refusal_accuracy": _rate(rows, "refusal_correct"), "latency_p95_ms": _percentile([row["latency_ms"] for row in rows if row.get("latency_ms") is not None], .95)}


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--dataset", type=Path, required=True); parser.add_argument("--output", type=Path, required=True); args = parser.parse_args()
    rows = [json.loads(line) for line in args.dataset.read_text(encoding="utf-8").splitlines() if line.strip()]
    ids = [row["id"] for row in rows]
    if len(ids) != len(set(ids)):
        parser.error("question ids must be unique")
    metrics = calculate_metrics(rows)
    coverage = {metric: sum(row.get(field) is not None for row in rows) for metric, field in RATE_FIELDS.items()}
    coverage["latency_p95_ms"] = sum(row.get("latency_ms") is not None for row in rows)
    result = {"mode": "annotation_summary", "count": len(rows), "metrics": metrics,
              "measurement_counts": coverage,
              "note": "No model calls are made. Null means unmeasured; this is not a live quality benchmark."}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__": main()
