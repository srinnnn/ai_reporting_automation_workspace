from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any

from intranet_app.storage import UserRecord


@dataclass(frozen=True)
class PermissionScope:
    brand_ids: frozenset[str]
    business_units: frozenset[str]
    platforms: frozenset[str]
    channels: frozenset[str]

    def __post_init__(self) -> None:
        for field_name, field_value in (
            ("brand_ids", self.brand_ids),
            ("business_units", self.business_units),
            ("platforms", self.platforms),
            ("channels", self.channels),
        ):
            if not isinstance(field_value, frozenset):
                raise TypeError(f"{field_name} must be frozenset")
            for item in field_value:
                if not isinstance(item, str) or not item:
                    raise ValueError(f"{field_name} must contain non-empty strings")


class PermissionService:
    def can_view_task(self, user: UserRecord, task: object) -> bool:
        _validate_user(user)
        _validate_task_object(task)
        role = _role_key(user.role)
        if role == "admin":
            return True
        if _task_created_by(task) == user.username:
            return True
        if role in {"business_owner", "viewer"} and _scope_matches(_parse_scope(user.role), task):
            return True
        logging.info("task view denied: user=%s role=%s task_id=%s", user.username, role, _task_id(task))
        return False

    def can_download_task(self, user: UserRecord, task: object) -> bool:
        _validate_user(user)
        _validate_task_object(task)
        if not self.can_view_task(user, task):
            return False
        if _task_status(task) != "success":
            return False
        result_asset = _task_result_asset(task)
        return isinstance(result_asset, dict) and bool(result_asset)

    def can_submit_task(self, user: UserRecord, task_type: object, payload: dict[str, Any]) -> bool:
        _validate_user(user)
        if not _task_type_text(task_type):
            raise ValueError("task_type must not be empty")
        if not isinstance(payload, dict):
            raise TypeError("payload must be dict")
        return _role_key(user.role) != "viewer"

    def filter_visible_tasks(self, user: UserRecord, tasks: list[object]) -> list[object]:
        _validate_user(user)
        if not isinstance(tasks, list):
            raise TypeError("tasks must be list")
        result = [task for task in tasks if self.can_view_task(user, task)]
        assert isinstance(result, list)
        return result


def _validate_user(user: UserRecord) -> None:
    if not isinstance(user, UserRecord):
        raise TypeError("user must be UserRecord")
    if not user.username.strip():
        raise ValueError("user.username must not be empty")
    if not user.role.strip():
        raise ValueError("user.role must not be empty")


def _validate_task_object(task: object) -> None:
    if task is None:
        raise TypeError("task must not be None")


def _role_key(role: str) -> str:
    if not isinstance(role, str):
        raise TypeError("role must be str")
    text = role.strip().lower()
    if not text:
        raise ValueError("role must not be empty")
    if any(marker in text for marker in ("admin", "administrator", "\u7ba1\u7406\u5458", "\u7cfb\u7edf\u7ba1\u7406\u5458")):
        return "admin"
    if any(marker in text for marker in ("business_owner", "business owner", "owner", "\u4e1a\u52a1\u8d1f\u8d23\u4eba", "\u8d1f\u8d23\u4eba")):
        return "business_owner"
    if any(marker in text for marker in ("viewer", "read_only", "readonly", "\u67e5\u770b\u8005", "\u53ea\u8bfb", "\u8bbf\u5ba2")):
        return "viewer"
    return "user"


def _parse_scope(role: str) -> PermissionScope:
    if not isinstance(role, str):
        raise TypeError("role must be str")
    scope_map: dict[str, set[str]] = {
        "brand_id": set(),
        "business_unit": set(),
        "platform": set(),
        "channel": set(),
    }
    for token in re.split(r"[|;]", role):
        if "=" not in token:
            continue
        key, raw_values = token.split("=", 1)
        normalized_key = key.strip().lower().replace("-", "_")
        values = {value.strip().lower() for value in raw_values.split(",") if value.strip()}
        if normalized_key in {"brand", "brand_id", "brand_ids"}:
            scope_map["brand_id"].update(values)
        elif normalized_key in {"department", "dept", "business_unit", "business_units"}:
            scope_map["business_unit"].update(values)
        elif normalized_key in {"platform", "platforms"}:
            scope_map["platform"].update(values)
        elif normalized_key in {"channel", "channels"}:
            scope_map["channel"].update(values)
    result = PermissionScope(
        brand_ids=frozenset(scope_map["brand_id"]),
        business_units=frozenset(scope_map["business_unit"]),
        platforms=frozenset(scope_map["platform"]),
        channels=frozenset(scope_map["channel"]),
    )
    assert isinstance(result, PermissionScope)
    return result


def _scope_matches(scope: PermissionScope, task: object) -> bool:
    if not isinstance(scope, PermissionScope):
        raise TypeError("scope must be PermissionScope")
    brand_id = _optional_task_text(task, "brand_id")
    business_unit = _optional_task_text(task, "business_unit")
    platform = _optional_task_text(task, "platform")
    channel = _optional_task_text(task, "channel")
    if scope.brand_ids and _matches_value(scope.brand_ids, brand_id):
        return True
    if scope.business_units and _matches_value(scope.business_units, business_unit):
        return True
    if scope.platforms and _matches_value(scope.platforms, platform):
        return True
    if scope.channels and _matches_value(scope.channels, channel):
        return True
    return False


def _matches_value(scope_values: frozenset[str], value: str) -> bool:
    if not isinstance(scope_values, frozenset):
        raise TypeError("scope_values must be frozenset")
    if not isinstance(value, str):
        raise TypeError("value must be str")
    normalized = value.strip().lower()
    return bool(normalized) and ("*" in scope_values or normalized in scope_values)


def _task_created_by(task: object) -> str:
    value = _optional_task_text(task, "created_by")
    if value:
        return value
    return _optional_task_text(task, "owner")


def _task_status(task: object) -> str:
    value = getattr(task, "status", "")
    if hasattr(value, "value"):
        value = value.value
    return str(value).strip().lower()


def _task_result_asset(task: object) -> object:
    result = getattr(task, "result", {})
    if not isinstance(result, dict):
        return None
    return result.get("result_asset")


def _task_type_text(task_type: object) -> str:
    value = task_type.value if hasattr(task_type, "value") else task_type
    return str(value).strip()


def _optional_task_text(task: object, field_name: str) -> str:
    value = getattr(task, field_name, "")
    if value is None:
        return ""
    return str(value).strip()


def _task_id(task: object) -> str:
    return _optional_task_text(task, "task_id") or _optional_task_text(task, "id") or "unknown"
