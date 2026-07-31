from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from backend.repositories.interfaces import TASK_STATUSES, TaskRepository
from intranet_app.storage import AutomationRunRecord, AutomationTaskRecord


@dataclass(frozen=True)
class TaskQueryFilters:
    task_type: str = ""
    status: str = ""
    created_by: str = ""

    def __post_init__(self) -> None:
        for field_name, field_value in (
            ("task_type", self.task_type),
            ("status", self.status),
            ("created_by", self.created_by),
        ):
            if not isinstance(field_value, str):
                raise TypeError(f"{field_name} must be str")
        if self.status and self.status not in TASK_STATUSES:
            raise ValueError("status must be pending, running, success, failed, or cancelled")


@dataclass(frozen=True)
class TaskReadModel:
    task_id: int
    task_type: str
    status: str
    created_by: str
    created_time: str
    result: dict[str, Any]
    error: str
    owner: str = ""
    brand_id: str = ""
    business_unit: str = ""
    platform: str = ""
    channel: str = ""
    updated_at: str = ""
    scope_snapshot: dict[str, Any] = field(default_factory=dict)
    result_asset: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.task_id, int) or self.task_id <= 0:
            raise ValueError("task_id must be positive int")
        for field_name, field_value in (
            ("task_type", self.task_type),
            ("status", self.status),
            ("created_by", self.created_by),
            ("created_time", self.created_time),
            ("error", self.error),
            ("owner", self.owner),
            ("brand_id", self.brand_id),
            ("business_unit", self.business_unit),
            ("platform", self.platform),
            ("channel", self.channel),
            ("updated_at", self.updated_at),
        ):
            if not isinstance(field_value, str):
                raise TypeError(f"{field_name} must be str")
        if not self.task_type.strip() or not self.status.strip() or not self.created_by.strip() or not self.created_time.strip():
            raise ValueError("task read fields must not be empty")
        if self.status not in TASK_STATUSES:
            raise ValueError("status must be pending, running, success, failed, or cancelled")
        if not isinstance(self.result, dict):
            raise TypeError("result must be dict")
        if not isinstance(self.scope_snapshot, dict):
            raise TypeError("scope_snapshot must be dict")
        if self.result_asset is not None and not isinstance(self.result_asset, dict):
            raise TypeError("result_asset must be dict or None")


@dataclass(frozen=True)
class TaskSummary:
    total: int
    success_count: int
    failed_count: int
    running_count: int
    pending_count: int

    def __post_init__(self) -> None:
        for field_name, field_value in (
            ("total", self.total),
            ("success_count", self.success_count),
            ("failed_count", self.failed_count),
            ("running_count", self.running_count),
            ("pending_count", self.pending_count),
        ):
            if not isinstance(field_value, int) or field_value < 0:
                raise ValueError(f"{field_name} must be non-negative int")
        if self.total < self.success_count + self.failed_count + self.running_count + self.pending_count:
            raise ValueError("total must cover counted statuses")


class TaskQueryService:
    def __init__(self, task_repository: TaskRepository) -> None:
        if not isinstance(task_repository, TaskRepository):
            raise TypeError("task_repository must be TaskRepository")
        self._task_repository = task_repository

    def get_task(self, task_id: int) -> TaskReadModel | None:
        if not isinstance(task_id, int) or task_id <= 0:
            raise ValueError("task_id must be positive int")
        task = self._task_repository.get_task(task_id)
        if task is None:
            return None
        latest_runs = _latest_runs_by_task_id(self._task_repository.list_task_runs())
        result = _build_read_model(task, latest_runs.get(task.id))
        assert isinstance(result, TaskReadModel)
        return result

    def list_tasks(self, filters: TaskQueryFilters | None = None) -> list[TaskReadModel]:
        if filters is None:
            filters = TaskQueryFilters()
        if not isinstance(filters, TaskQueryFilters):
            raise TypeError("filters must be TaskQueryFilters")
        latest_runs = _latest_runs_by_task_id(self._task_repository.list_task_runs())
        rows = [_build_read_model(task, latest_runs.get(task.id)) for task in self._task_repository.list_tasks()]
        result = [row for row in rows if _matches_filters(row, filters)]
        assert isinstance(result, list)
        return result

    def list_failed_tasks(self) -> list[TaskReadModel]:
        result = self.list_tasks(TaskQueryFilters(status="failed"))
        assert isinstance(result, list)
        return result

    def get_task_summary(self) -> TaskSummary:
        tasks = self.list_tasks()
        success_count = sum(1 for task in tasks if task.status == "success")
        failed_count = sum(1 for task in tasks if task.status == "failed")
        running_count = sum(1 for task in tasks if task.status == "running")
        pending_count = sum(1 for task in tasks if task.status == "pending")
        result = TaskSummary(
            total=len(tasks),
            success_count=success_count,
            failed_count=failed_count,
            running_count=running_count,
            pending_count=pending_count,
        )
        assert isinstance(result, TaskSummary)
        return result


def _latest_runs_by_task_id(runs: list[AutomationRunRecord]) -> dict[int, AutomationRunRecord]:
    if not isinstance(runs, list):
        raise TypeError("runs must be list")
    latest: dict[int, AutomationRunRecord] = {}
    for run in runs:
        if not isinstance(run, AutomationRunRecord):
            raise TypeError("each run must be AutomationRunRecord")
        latest.setdefault(run.task_id, run)
    assert isinstance(latest, dict)
    return latest


def _build_read_model(task: AutomationTaskRecord, latest_run: AutomationRunRecord | None) -> TaskReadModel:
    if not isinstance(task, AutomationTaskRecord):
        raise TypeError("task must be AutomationTaskRecord")
    if latest_run is not None and not isinstance(latest_run, AutomationRunRecord):
        raise TypeError("latest_run must be AutomationRunRecord")
    status = _task_status(task, latest_run)
    error = _task_error(latest_run)
    result = _task_result(latest_run)
    result_asset = _task_result_asset(result)
    read_model = TaskReadModel(
        task_id=task.id,
        task_type=task.file_type,
        status=status,
        created_by=task.owner,
        created_time=task.created_at,
        result=result,
        error=error,
        owner=task.owner,
        brand_id=task.brand_id,
        business_unit=task.business_unit,
        platform=task.platform,
        channel=task.channel,
        updated_at=task.updated_at,
        scope_snapshot=_scope_snapshot(task),
        result_asset=result_asset,
    )
    assert isinstance(read_model, TaskReadModel)
    return read_model


def _task_status(task: AutomationTaskRecord, latest_run: AutomationRunRecord | None) -> str:
    if latest_run is not None and latest_run.status in TASK_STATUSES:
        return latest_run.status
    if not task.enabled:
        return "cancelled"
    return "pending"


def _task_error(latest_run: AutomationRunRecord | None) -> str:
    if latest_run is None or latest_run.status != "failed":
        return ""
    prefix = "error:"
    if latest_run.message.lower().startswith(prefix):
        return latest_run.message[len(prefix) :].strip()
    return latest_run.message.strip()


def _task_result(latest_run: AutomationRunRecord | None) -> dict[str, Any]:
    if latest_run is None or latest_run.status == "failed":
        return {}
    message = latest_run.message.strip()
    if not message:
        return {}
    try:
        parsed = json.loads(message)
    except json.JSONDecodeError:
        return {"message": message}
    if isinstance(parsed, dict):
        return parsed
    return {"message": message}


def _task_result_asset(result: dict[str, Any]) -> dict[str, Any] | None:
    if not isinstance(result, dict):
        raise TypeError("result must be dict")
    asset = result.get("result_asset")
    if asset is None:
        return None
    if not isinstance(asset, dict):
        return None
    parsed = dict(asset)
    assert isinstance(parsed, dict)
    return parsed


def _scope_snapshot(task: AutomationTaskRecord) -> dict[str, Any]:
    if not isinstance(task, AutomationTaskRecord):
        raise TypeError("task must be AutomationTaskRecord")
    snapshot = {
        "owner": task.owner,
        "brand_id": task.brand_id,
        "business_unit": task.business_unit,
        "platform": task.platform,
        "channel": task.channel,
        "source": "automation_tasks",
        "policy_version": "task-read-model-v1",
    }
    assert isinstance(snapshot, dict)
    return snapshot


def _matches_filters(task: TaskReadModel, filters: TaskQueryFilters) -> bool:
    if filters.task_type and task.task_type != filters.task_type:
        return False
    if filters.status and task.status != filters.status:
        return False
    if filters.created_by and task.created_by != filters.created_by:
        return False
    return True
