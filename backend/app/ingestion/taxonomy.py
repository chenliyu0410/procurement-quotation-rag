from enum import StrEnum


class NormalizedCategory(StrEnum):
    WORKS = "工程"
    GOODS = "財物"
    SERVICES = "勞務"
    IT_SERVICES = "資訊服務"
    OTHER = "其他"


TAXONOMY_VERSION = "v1"


def normalize_category(raw: str, case_name: str) -> NormalizedCategory:
    text = f"{raw} {case_name}".casefold()
    if any(word in text for word in ("資訊", "系統", "軟體", "網路", "數位", "維護")):
        return NormalizedCategory.IT_SERVICES
    if any(word in text for word in ("工程", "施工", "道路", "建築")):
        return NormalizedCategory.WORKS
    if any(word in text for word in ("財物", "設備", "器材", "採購")):
        return NormalizedCategory.GOODS
    if any(word in text for word in ("勞務", "服務", "顧問", "清潔")):
        return NormalizedCategory.SERVICES
    return NormalizedCategory.OTHER
