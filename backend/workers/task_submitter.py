from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone

from backend.services.task_service import TaskCreateRequest, TaskResultSaveRequest, TaskService, TaskStatus
from backend.workers.contracts import JsonObject, TaskRequest, TaskResult, TaskType, WorkerTaskStatus
from backend.workers.task_runner import TaskRunner


@dataclass(frozen=True)
class TaskSubmitter:
    task_service: TaskService
    task_runner: TaskRunner

    def __post_init__(self) -> None:
        if not isinstance(self.task_service, TaskService):
            raise TypeError("task_service must be TaskService")
        if not isinstance(self.task_runner, TaskRunner):
            raise TypeError("task_runner must be TaskRunner")

    def submit(self, task_type: TaskType | str, payload: JsonObject, created_by: str) -> TaskResult:
        normalized_task_type = _normalize_task_type(task_type)
        if not isinstance(payload, dict):
            raise TypeError("payload must be dict")
        if not isinstance(created_by, str) or not created_by.strip():
            raise ValueError("created_by must not be empty")

        task_id = self.task_service.create_task(_build_task_create_request(normalized_task_type, payload, created_by.strip()))
        task_request = TaskRequest(
            task_id=task_id,
            task_type=normalized_task_type,
            created_by=created_by.strip(),
            payload=payload,
            created_time=_utc_now(),
        )
        task_result = self.task_runner.run(task_request)
        self.task_service.save_task_result(
            TaskResultSaveRequest(
                task_id=task_result.task_id,
                status=_task_status(task_result.status),
                run_date=_run_date(payload),
                result_message=_result_message(task_result),
                error_message=task_result.error,
                executed_by=created_by.strip(),
            )
        )
        logging.info("task submitted through TaskSubmitter: task=%s type=%s status=%s", task_id, normalized_task_type.value, task_result.status.value)
        assert isinstance(task_result, TaskResult)
        return task_result


def _normalize_task_type(task_type: TaskType | str) -> TaskType:
    if isinstance(task_type, TaskType):
        return task_type
    if not isinstance(task_type, str) or not task_type.strip():
        raise ValueError("task_type must not be empty")
    normalized = task_type.strip()
    for candidate in TaskType:
        if normalized in {candidate.name, candidate.value}:
            return candidate
    raise ValueError("unsupported task_type")


def _build_task_create_request(task_type: TaskType, payload: JsonObject, created_by: str) -> TaskCreateRequest:
    if not isinstance(task_type, TaskType):
        raise TypeError("task_type must be TaskType")
    if not isinstance(payload, dict):
        raise TypeError("payload must be dict")
    metadata = payload.get("metadata")
    metadata_payload = metadata if isinstance(metadata, dict) else {}
    brand_id = _text_from(payload, metadata_payload, "brand_id")
    date_window = _date_window(payload, metadata_payload)
    result = TaskCreateRequest(
        task_name=_optional_text(payload, "task_name") or f"{task_type.value}:{brand_id}:{date_window}",
        business_unit=_text_from(payload, metadata_payload, "business_unit"),
        brand_id=brand_id,
        brand_name=_text_from(payload, metadata_payload, "brand_name"),
        platform=_text_from(payload, metadata_payload, "platform"),
        channel=_text_from(payload, metadata_payload, "channel"),
        task_type=task_type.value,
        frequency=_frequency(payload, task_type),
        scheduled_time=_optional_text(payload, "scheduled_time") or "00:00",
        date_window=date_window,
        output_folder=_optional_text(payload, "output_folder") or "runtime/results",
        owner=created_by,
        notes=_optional_text(payload, "notes") or "",
    )
    assert isinstance(result, TaskCreateRequest)
    return result


def _task_status(status: WorkerTaskStatus) -> TaskStatus:
    if not isinstance(status, WorkerTaskStatus):
        raise TypeError("status must be WorkerTaskStatus")
    return TaskStatus(status.value)


def _result_message(task_result: TaskResult) -> str:
    if not isinstance(task_result, TaskResult):
        raise TypeError("task_result must be TaskResult")
    if task_result.status == WorkerTaskStatus.FAILED:
        return ""
    return json.dumps(task_result.result, ensure_ascii=False, sort_keys=True)


def _frequency(payload: JsonObject, task_type: TaskType) -> str:
    value = _optional_text(payload, "frequency")
    if value:
        return value
    report_period = _optional_text(payload, "report_period")
    if report_period in {"daily", "weekly", "monthly"}:
        return report_period
    if task_type == TaskType.DATA_IMPORT:
        return "daily"
    return "daily"


def _run_date(payload: JsonObject) -> str:
    return _optional_text(payload, "run_date") or _date_window(payload, _metadata_payload(payload))


def _date_window(payload: JsonObject, metadata_payload: dict[object, object]) -> str:
    value = _optional_text(payload, "date_window")
    if value:
        return value
    report_date = _optional_text(payload, "report_date")
    if report_date:
        return report_date
    start_date = _optional_text(payload, "start_date") or _optional_text(metadata_payload, "data_start_date")
    end_date = _optional_text(payload, "end_date") or _optional_text(metadata_payload, "data_end_date")
    if start_date and end_date:
        return f"{start_date}-{end_date}"
    raise ValueError("date_window, report_date, or start/end date must be provided")


def _metadata_payload(payload: JsonObject) -> dict[object, object]:
    value = payload.get("metadata")
    return value if isinstance(value, dict) else {}


def _text_from(payload: JsonObject, metadata_payload: dict[object, object], field_name: str) -> str:
    value = _optional_text(payload, field_name) or _optional_text(metadata_payload, field_name)
    if not value:
        raise ValueError(f"{field_name} must not be empty")
    assert value
    return value


def _optional_text(payload: dict[object, object], field_name: str) -> str:
    value = payload.get(field_name)
    if value is None:
        return ""
    if not isinstance(value, str):
        return ""
    result = value.strip()
    assert isinstance(result, str)
    return result


def _utc_now() -> str:
    result = datetime.now(timezone.utc).isoformat()
    assert result
    return result
