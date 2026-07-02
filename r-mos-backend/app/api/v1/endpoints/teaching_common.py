"""
Teaching domain shared helpers.
Avoids circular import between teaching.py and teaching_roster.py.
"""
from typing import Any, Optional

from app.core.exceptions import BusinessRuleViolation, ResourceNotFoundError


def _raise_business_error(exc: BusinessRuleViolation) -> None:
    raise exc


def _raise_not_found(exc: ResourceNotFoundError) -> None:
    # 直接抛出类型化的 ResourceNotFoundError，交由 main.py 的专用处理器映射为
    # 404 + error_type="ResourceNotFoundError" + 结构化 details；
    # 此前转成通用 HTTPException 会命中兜底处理器，error_type 丢失为 "HTTPException"。
    raise exc


def _parse_user_id(raw_user_id: Optional[str]) -> Optional[int]:
    if raw_user_id is None:
        return None
    value = raw_user_id.strip()
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _to_int_or_none(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
