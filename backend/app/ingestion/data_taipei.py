import csv
import io
import hashlib
import json
import re
import ssl
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import httpx
import truststore

from app.ingestion.normalize import CaseRecord


@dataclass(frozen=True)
class ApiSnapshot:
    rows: list[dict[str, Any]]
    checksum: str
    resource_id: str


def fetch_api(url: str, *, client: httpx.Client | None = None, page_size: int = 1000,
              max_records: int = 100000) -> ApiSnapshot:
    """Read a complete resourceAquire snapshot before any database mutation.

    System trust validates certificates and hostnames without disabling TLS.
    Snapshot consistency checks detect common paging races, but the platform
    does not provide a transactional snapshot token.
    """
    endpoint = httpx.URL(url)
    match = re.fullmatch(r"/api/v1/dataset/([a-fA-F0-9-]{36})/?", endpoint.path)
    if endpoint.scheme != "https" or endpoint.host != "data.taipei" or not match:
        raise ValueError("Expected an HTTPS data.taipei /api/v1/dataset/<resource-id> URL")
    if not 1 <= page_size <= 1000 or max_records < 1:
        raise ValueError("page_size must be 1..1000 and max_records must be positive")
    if client is None:
        context = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        with httpx.Client(verify=context, timeout=30) as owned:
            return fetch_api(url, client=owned, page_size=page_size, max_records=max_records)

    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    total = None
    while total is None or len(rows) < total:
        offset = len(rows)
        response = client.get(endpoint, params={**dict(endpoint.params), "scope": "resourceAquire",
                                               "limit": page_size, "offset": offset, "sort": "_id"}, follow_redirects=False)
        response.raise_for_status()
        payload = response.json()
        result = payload.get("result") if isinstance(payload, dict) else None
        if not isinstance(result, dict):
            raise ValueError("API response is missing result")
        count, page = result.get("count"), result.get("results")
        if type(count) is not int or not 0 <= count <= max_records or not isinstance(page, list):
            raise ValueError("API returned an invalid count/results or exceeded max_records")
        if result.get("offset") != offset:
            raise ValueError("API offset does not match the requested page")
        if total is not None and count != total:
            raise ValueError("API count changed during pagination; retry the full sync")
        total = count
        if len(page) > page_size or offset + len(page) > total or (not page and offset < total):
            raise ValueError("API returned an incomplete or inconsistent page")
        for row in page:
            if not isinstance(row, dict) or type(row.get("_id")) not in (int, str):
                raise ValueError("API rows must be objects with an _id")
            identity = str(row["_id"])
            if identity in seen:
                raise ValueError("API repeated a row during pagination; retry the full sync")
            seen.add(identity)
            rows.append(row)
    content = json.dumps(rows, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return ApiSnapshot(rows, hashlib.sha256(content).hexdigest(), match.group(1))


def parse_csv(content: bytes, normalizer: Callable[..., CaseRecord], *, source_period: str, source_url: str) -> list[CaseRecord]:
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = content.decode("big5")
    return [normalizer(row, source_period=source_period, source_url=source_url) for row in csv.DictReader(io.StringIO(text))]
