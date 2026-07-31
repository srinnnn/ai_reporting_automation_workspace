from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import TypeAlias


JsonScalar: TypeAlias = str | int | bool | None
JsonValue: TypeAlias = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]
JsonObject: TypeAlias = dict[str, JsonValue]


class TaskType(str, Enum):
    DATA_IMPORT = "DATA_IMPORT"
    REPORT_GENERATE = "REPORT_GENERATE"
    AI_CONTENT_GENERATE = "AI_CONTENT_GENERATE"


class WorkerTaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class TaskRequest:
    task_id: int
    task_type: TaskType
    created_by: str
    payload: JsonObject
    created_time: str

    def __post_init__(self) -> None:
        if not isinstance(self.task_id, int) or self.task_id <= 0:
            raise ValueError("task_id must be positive int")
        if not isinstance(self.task_type, TaskType):
            raise TypeError("task_type must be TaskType")
        if not isinstance(self.created_by, str) or not self.created_by.strip():
            raise ValueError("created_by must not be empty")
        if not isinstance(self.payload, dict):
            raise TypeError("payload must be dict")
        _assert_json_object(self.payload, "payload")
        _assert_iso_time(self.created_time, "created_time")


@dataclass(frozen=True)
class TaskResult:
    task_id: int
    status: WorkerTaskStatus
    result: JsonObject
    error: str
    finished_time: str

    def __post_init__(self) -> None:
        if not isinstance(self.task_id, int) or self.task_id <= 0:
            raise ValueError("task_id must be positive int")
        if not isinstance(self.status, WorkerTaskStatus):
            raise TypeError("status must be WorkerTaskStatus")
        if not isinstance(self.result, dict):
            raise TypeError("result must be dict")
        _assert_json_object(self.result, "result")
        if not isinstance(self.error, str):
            raise TypeError("error must be str")
        if self.status == WorkerTaskStatus.FAILED and not self.error.strip():
            raise ValueError("failed task result must include error")
        _assert_iso_time(self.finished_time, "finished_time")


def _assert_iso_time(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must not be empty")
    normalized = value.strip().replace("Z", "+00:00")
    try:
        datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be ISO datetime text") from exc


def _assert_json_object(value: JsonObject, field_name: str) -> None:
    if not isinstance(value, dict):
        raise TypeError(f"{field_name} must be dict")
    for key, item in value.items():
        if not isinstance(key, str) or not key.strip():
            raise ValueError(f"{field_name} keys must be non-empty strings")
        _assert_json_value(item, f"{field_name}.{key}")


def _assert_json_value(value: JsonValue, field_name: str) -> None:
    if value is None or isinstance(value, (str, int, bool)):
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _assert_json_value(item, f"{field_name}[{index}]")
        return
    if isinstance(value, dict):
        _assert_json_object(value, field_name)
        return
    raise TypeError(f"{field_name} must be JSON-compatible")
