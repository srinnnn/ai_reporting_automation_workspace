from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum

from backend.repositories.interfaces import AutomationTaskCreate, TaskRepository, TaskRunCreate
from intranet_app.storage import AutomationTaskRecord


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class TaskCreateRequest:
    task_name: str
    business_unit: str
    brand_id: str
    brand_name: str
    platform: str
    channel: str
    task_type: str
    frequency: str
    scheduled_time: str
    date_window: str
    output_folder: str
    owner: str
    notes: str = ""

    def __post_init__(self) -> None:
        for field_name, field_value in (
            ("task_name", self.task_name),
            ("business_unit", self.business_unit),
            ("brand_id", self.brand_id),
            ("brand_name", self.brand_name),
            ("platform", self.platform),
            ("channel", self.channel),
            ("task_type", self.task_type),
            ("frequency", self.frequency),
            ("scheduled_time", self.scheduled_time),
            ("date_window", self.date_window),
            ("output_folder", self.output_folder),
            ("owner", self.owner),
        ):
            if not isinstance(field_value, str) or not field_value.strip():
                raise ValueError(f"{field_name} must not be empty")
        if not isinstance(self.notes, str):
            raise TypeError("notes must be str")


@dataclass(frozen=True)
class TaskStatusUpdate:
    task_id: int
    status: TaskStatus
    executed_by: str
    run_date: str = "system"
    result_message: str = ""
    error_message: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.task_id, int) or self.task_id <= 0:
            raise ValueError("task_id must be positive int")
        if not isinstance(self.status, TaskStatus):
            raise TypeError("status must be TaskStatus")
        for field_name, field_value in (("executed_by", self.executed_by), ("run_date", self.run_date)):
            if not isinstance(field_value, str) or not field_value.strip():
                raise ValueError(f"{field_name} must not be empty")
        for field_name, field_value in (("result_message", self.result_message), ("error_message", self.error_message)):
            if not isinstance(field_value, str):
                raise TypeError(f"{field_name} must be str")


@dataclass(frozen=True)
class TaskResultSaveRequest:
    task_id: int
    status: TaskStatus
    run_date: str
    result_message: str
    error_message: str
    executed_by: str

    def __post_init__(self) -> None:
        if not isinstance(self.task_id, int) or self.task_id <= 0:
            raise ValueError("task_id must be positive int")
        if not isinstance(self.status, TaskStatus):
            raise TypeError("status must be TaskStatus")
        for field_name, field_value in (
            ("run_date", self.run_date),
            ("executed_by", self.executed_by),
        ):
            if not isinstance(field_value, str) or not field_value.strip():
                raise ValueError(f"{field_name} must not be empty")
        for field_name, field_value in (
            ("result_message", self.result_message),
            ("error_message", self.error_message),
        ):
            if not isinstance(field_value, str):
                raise TypeError(f"{field_name} must be str")
        if self.status == TaskStatus.FAILED and not self.error_message.strip():
            raise ValueError("failed task must include error_message")


class TaskService:
    def __init__(self, task_repository: TaskRepository) -> None:
        if not isinstance(task_repository, TaskRepository):
            raise TypeError("task_repository must be TaskRepository")
        self._task_repository = task_repository

    def create_task(self, request: TaskCreateRequest) -> int:
        if not isinstance(request, TaskCreateRequest):
            raise TypeError("request must be TaskCreateRequest")
        task_id = self._task_repository.create_task(
            AutomationTaskCreate(
                task_name=request.task_name,
                business_unit=request.business_unit,
                brand_id=request.brand_id,
                brand_name=request.brand_name,
                platform=request.platform,
                channel=request.channel,
                file_type=request.task_type,
                frequency=request.frequency,
                scheduled_time=request.scheduled_time,
                date_window=request.date_window,
                enabled=True,
                output_folder=request.output_folder,
                owner=request.owner,
                notes=request.notes,
            )
        )
        logging.info("task created through TaskService: task=%s", task_id)
        assert task_id > 0
        return task_id

    def get_task(self, task_id: int) -> AutomationTaskRecord | None:
        if not isinstance(task_id, int) or task_id <= 0:
            raise ValueError("task_id must be positive int")
        task = self._task_repository.get_task(task_id)
        assert task is None or isinstance(task, AutomationTaskRecord)
        return task

    def update_task_status(self, request: TaskStatusUpdate) -> int:
        if not isinstance(request, TaskStatusUpdate):
            raise TypeError("request must be TaskStatusUpdate")
        run_id = self._task_repository.save_task_result(
            TaskRunCreate(
                task_id=request.task_id,
                run_date=request.run_date,
                status=request.status.value,
                result_message=request.result_message,
                error_message=request.error_message,
                executed_by=request.executed_by,
            )
        )
        logging.info("task status recorded through TaskService: task=%s status=%s", request.task_id, request.status.value)
        assert run_id > 0
        return run_id

    def save_task_result(self, request: TaskResultSaveRequest) -> int:
        if not isinstance(request, TaskResultSaveRequest):
            raise TypeError("request must be TaskResultSaveRequest")
        run_id = self._task_repository.save_task_result(
            TaskRunCreate(
                task_id=request.task_id,
                run_date=request.run_date,
                status=request.status.value,
                result_message=request.result_message,
                error_message=request.error_message,
                executed_by=request.executed_by,
            )
        )
        logging.info("task result saved through TaskService: task=%s status=%s", request.task_id, request.status.value)
        assert run_id > 0
        return run_id
