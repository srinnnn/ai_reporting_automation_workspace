from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from backend.services.permission_service import PermissionService
from backend.services.task_query_service import TaskQueryFilters, TaskQueryService, TaskReadModel
from backend.services.task_result_service import TaskResultService
from intranet_app.storage import UserRecord


@dataclass(frozen=True)
class TaskConsoleFilters:
    task_type: str = ""
    status: str = ""
    created_by: str = ""
    brand_id: str = ""
    business_unit: str = ""
    platform: str = ""
    channel: str = ""

    def __post_init__(self) -> None:
        for field_name, field_value in (
            ("task_type", self.task_type),
            ("status", self.status),
            ("created_by", self.created_by),
            ("brand_id", self.brand_id),
            ("business_unit", self.business_unit),
            ("platform", self.platform),
            ("channel", self.channel),
        ):
            if not isinstance(field_value, str):
                raise TypeError(f"{field_name} must be str")


@dataclass(frozen=True)
class TaskConsoleService:
    task_query: TaskQueryService
    task_result: TaskResultService
    permissions: PermissionService

    def __post_init__(self) -> None:
        if not isinstance(self.task_query, TaskQueryService):
            raise TypeError("task_query must be TaskQueryService")
        if not isinstance(self.task_result, TaskResultService):
            raise TypeError("task_result must be TaskResultService")
        if not isinstance(self.permissions, PermissionService):
            raise TypeError("permissions must be PermissionService")

    def list_visible_tasks(self, user: UserRecord, filters: TaskConsoleFilters | None = None) -> dict[str, object]:
        _validate_user(user)
        actual_filters = filters if filters is not None else TaskConsoleFilters()
        if not isinstance(actual_filters, TaskConsoleFilters):
            raise TypeError("filters must be TaskConsoleFilters")
        query_filters = TaskQueryFilters(
            task_type=actual_filters.task_type,
            status=actual_filters.status,
            created_by=actual_filters.created_by,
        )
        tasks = self.task_query.list_tasks(query_filters)
        tasks = _filter_extra_fields(tasks, actual_filters)
        visible_tasks = tasks if _can_view_all_tasks(user) else self.permissions.filter_visible_tasks(user, tasks)
        payload = {
            "tasks": [_task_list_payload(task) for task in visible_tasks],
            "total": len(visible_tasks),
        }
        assert isinstance(payload["tasks"], list)
        return payload

    def get_task_detail(self, user: UserRecord, task_id: int) -> dict[str, object]:
        _validate_user(user)
        if not isinstance(task_id, int) or task_id <= 0:
            raise ValueError("task_id must be positive int")
        task = self.task_query.get_task(task_id)
        if task is None:
            raise FileNotFoundError(str(task_id))
        if not _can_view_all_tasks(user) and not self.permissions.can_view_task(user, task):
            raise PermissionError("forbidden")
        payload = _task_detail_payload(task)
        payload.update(_safe_result_payload(self.task_result, task))
        assert payload["task_id"] == task.task_id
        return payload


def _validate_user(user: UserRecord) -> None:
    if not isinstance(user, UserRecord):
        raise TypeError("user must be UserRecord")


def _can_view_all_tasks(user: UserRecord) -> bool:
    role = _role_key(user.role)
    return role in {"admin", "developer"}


def _role_key(role: str) -> str:
    if not isinstance(role, str):
        raise TypeError("role must be str")
    text = role.strip().lower()
    if not text:
        raise ValueError("role must not be empty")
    if any(marker in text for marker in ("admin", "administrator", "管理员", "系统管理员")):
        return "admin"
    if any(marker in text for marker in ("developer", "dev", "开发", "开发者", "运维")):
        return "developer"
    if any(marker in text for marker in ("business_owner", "business owner", "owner", "业务负责人", "负责人")):
        return "business_owner"
    if any(marker in text for marker in ("viewer", "read_only", "readonly", "查看者", "只读", "访客")):
        return "viewer"
    return "user"


def _filter_extra_fields(tasks: list[TaskReadModel], filters: TaskConsoleFilters) -> list[TaskReadModel]:
    if not isinstance(tasks, list):
        raise TypeError("tasks must be list")
    result = [task for task in tasks if _matches_extra_fields(task, filters)]
    assert isinstance(result, list)
    return result


def _matches_extra_fields(task: TaskReadModel, filters: TaskConsoleFilters) -> bool:
    if not isinstance(task, TaskReadModel):
        raise TypeError("task must be TaskReadModel")
    if filters.brand_id and task.brand_id != filters.brand_id:
        return False
    if filters.business_unit and task.business_unit != filters.business_unit:
        return False
    if filters.platform and task.platform != filters.platform:
        return False
    if filters.channel and task.channel != filters.channel:
        return False
    return True


def _task_list_payload(task: TaskReadModel) -> dict[str, object]:
    if not isinstance(task, TaskReadModel):
        raise TypeError("task must be TaskReadModel")
    payload = {
        "task_id": task.task_id,
        "task_type": task.task_type,
        "status": task.status,
        "created_by": task.created_by,
        "created_time": task.created_time,
        "updated_at": task.updated_at,
        "brand_id": task.brand_id,
        "business_unit": task.business_unit,
        "platform": task.platform,
        "channel": task.channel,
        "error": task.error,
        "result_asset": _safe_asset(task.result_asset),
    }
    assert payload["task_id"] == task.task_id
    return payload


def _task_detail_payload(task: TaskReadModel) -> dict[str, object]:
    payload = _task_list_payload(task)
    payload["result_summary"] = _result_summary(task.result)
    return payload


def _safe_result_payload(task_result: TaskResultService, task: TaskReadModel) -> dict[str, object]:
    if task.status != "success":
        return {"filename": "", "file_path": "", "downloadable": False}
    try:
        view = task_result.get_result(task.task_id)
    except (FileNotFoundError, ValueError, PermissionError):
        return {"filename": "", "file_path": "", "downloadable": False}
    return {
        "result_asset": dict(view.result_asset),
        "filename": view.filename,
        "file_path": view.file_path,
        "downloadable": True,
    }


def _safe_asset(asset: dict[str, Any] | None) -> dict[str, object]:
    if not isinstance(asset, dict):
        return {}
    result: dict[str, object] = {}
    filename = asset.get("filename")
    size = asset.get("size")
    if isinstance(filename, str) and filename.strip():
        result["filename"] = filename.strip()
    if isinstance(size, int) and size >= 0:
        result["size"] = size
    return result


def _result_summary(result: dict[str, Any]) -> dict[str, object]:
    if not isinstance(result, dict):
        raise TypeError("result must be dict")
    summary: dict[str, object] = {}
    for key, value in result.items():
        if key == "result_asset":
            continue
        if isinstance(value, (str, int, bool)) or value is None:
            summary[key] = value
    return summary