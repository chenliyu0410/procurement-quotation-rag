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
    source_record_id: str | None = None,
) -> str:
    dataset = _normalize(source_dataset)
    number = _normalize(case_number or "")
    if source_record_id:
        identity_input = f"{dataset}|resource-row|{_normalize(source_record_id)}"
    elif number:
        identity_input = f"{dataset}|number|{number}"
    else:
        identity_input = f"{dataset}|derived|{_normalize(agency)}|{_normalize(case_name)}|{year}"
    return hashlib.sha256(identity_input.encode("utf-8")).hexdigest()
