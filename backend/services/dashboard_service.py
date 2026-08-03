from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from backend.services.permission_service import PermissionService
from backend.services.system_status_service import SystemStatusService
from backend.services.task_query_service import TaskQueryService
from intranet_app.storage import UserRecord


@dataclass(frozen=True)
class DashboardService:
    system_status: SystemStatusService
    task_query: TaskQueryService
    permissions: PermissionService

    def __post_init__(self) -> None:
        if not isinstance(self.system_status, SystemStatusService):
            raise TypeError("system_status must be SystemStatusService")
        if not isinstance(self.task_query, TaskQueryService):
            raise TypeError("task_query must be TaskQueryService")
        if not isinstance(self.permissions, PermissionService):
            raise TypeError("permissions must be PermissionService")

    def get_dashboard(self, user: UserRecord) -> dict[str, object]:
        _validate_user(user)
        role = _role_key(user.role)
        if role == "viewer":
            raise PermissionError("forbidden")
        if role in {"admin", "developer"}:
            tasks = self.task_query.list_tasks()
            system_status = _full_system_status(self.system_status, user)
        else:
            all_tasks = self.task_query.list_tasks()
            tasks = self.permissions.filter_visible_tasks(user, all_tasks)
            system_status = {"available": False, "reason": "business_scope_only"}
        failed_tasks = [task for task in tasks if _task_status(task) == "failed"]
        payload = {
            "system_status": system_status,
            "task_summary": _task_summary(tasks),
            "recent_failed_tasks": [_failed_task_payload(task) for task in failed_tasks[:10]],
        }
        assert isinstance(payload["task_summary"], dict)
        return payload


def _validate_user(user: UserRecord) -> None:
    if not isinstance(user, UserRecord):
        raise TypeError("user must be UserRecord")


def _full_system_status(system_status: SystemStatusService, user: UserRecord) -> dict[str, object]:
    health = system_status.get_health_status(user)
    components = health.get("components", [])
    if not isinstance(components, list):
        components = []
    component_map = {str(item.get("name", "")): item for item in components if isinstance(item, dict)}
    payload = {
        "application": {
            "status": health.get("status", "warning"),
            "environment": health.get("environment", ""),
        },
        "database": _component_payload(component_map.get("database")),
        "storage": _component_payload(component_map.get("filesystem")),
        "ai": _component_payload(component_map.get("ai")),
    }
    assert "application" in payload
    return payload


def _component_payload(component: object) -> dict[str, object]:
    if not isinstance(component, dict):
        return {"status": "warning", "message": "component status is unavailable"}
    status = component.get("status", "warning")
    message = component.get("message", "")
    return {
        "status": str(status),
        "message": str(message),
    }


def _task_summary(tasks: list[object]) -> dict[str, int]:
    if not isinstance(tasks, list):
        raise TypeError("tasks must be list")
    summary = {
        "total": len(tasks),
        "pending": sum(1 for task in tasks if _task_status(task) == "pending"),
        "running": sum(1 for task in tasks if _task_status(task) == "running"),
        "success": sum(1 for task in tasks if _task_status(task) == "success"),
        "failed": sum(1 for task in tasks if _task_status(task) == "failed"),
    }
    assert summary["total"] >= 0
    return summary


def _failed_task_payload(task: object) -> dict[str, object]:
    payload = {
        "task_id": _task_id(task),
        "task_type": _task_text(task, "task_type"),
        "created_by": _task_text(task, "created_by"),
        "error": _task_text(task, "error"),
        "updated_at": _task_text(task, "updated_at"),
    }
    assert "task_id" in payload
    return payload


def _task_status(task: object) -> str:
    return _task_text(task, "status").lower()


def _task_id(task: object) -> int:
    value = getattr(task, "task_id", 0)
    if not isinstance(value, int):
        return 0
    return value


def _task_text(task: object, field_name: str) -> str:
    value = getattr(task, field_name, "")
    if value is None:
        return ""
    return str(value).strip()


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