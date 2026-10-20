import csv
import io
from collections.abc import Callable

from app.ingestion.normalize import CaseRecord


def parse_csv(content: bytes, normalizer: Callable[..., CaseRecord], *, source_period: str, source_url: str) -> list[CaseRecord]:
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = content.decode("big5")
    return [normalizer(row, source_period=source_period, source_url=source_url) for row in csv.DictReader(io.StringIO(text))]
