import hashlib
import re
import unicodedata


def _normalize(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).strip().casefold()
    return re.sub(r"\s+", "", normalized)


def build_case_identity(
    source_dataset: str,
    case_number: str | None,
    agency: str,
    case_name: str,
    year: int,
) -> str:
    dataset = _normalize(source_dataset)
    number = _normalize(case_number or "")
    if number:
        identity_input = f"{dataset}|number|{number}"
    else:
        identity_input = f"{dataset}|derived|{_normalize(agency)}|{_normalize(case_name)}|{year}"
    return hashlib.sha256(identity_input.encode("utf-8")).hexdigest()
