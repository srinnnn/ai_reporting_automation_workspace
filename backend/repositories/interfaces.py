from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from intranet_app.storage import AutomationRunRecord, AutomationTaskRecord, JobRecord, UserRecord


TASK_STATUSES = ("pending", "running", "success", "failed", "cancelled")


@dataclass(frozen=True)
class UserCreate:
    username: str
    password: str
    display_name: str
    role: str

    def __post_init__(self) -> None:
        for field_name, field_value in (
            ("username", self.username),
            ("password", self.password),
            ("display_name", self.display_name),
            ("role", self.role),
        ):
            if not isinstance(field_value, str) or not field_value.strip():
                raise ValueError(f"{field_name} must not be empty")


@dataclass(frozen=True)
class ReportCreate:
    module: str
    title: str
    brand: str
    business_type: str
    created_by: str
    input_file: Path
    result_file: Path
    summary: dict[str, str]
    warnings: list[str]

    def __post_init__(self) -> None:
        for field_name, field_value in (
            ("module", self.module),
            ("title", self.title),
            ("brand", self.brand),
            ("business_type", self.business_type),
            ("created_by", self.created_by),
        ):
            if not isinstance(field_value, str) or not field_value.strip():
                raise ValueError(f"{field_name} must not be empty")
        if not isinstance(self.input_file, Path):
            raise TypeError("input_file must be pathlib.Path")
        if not isinstance(self.result_file, Path):
            raise TypeError("result_file must be pathlib.Path")
        if not isinstance(self.summary, dict):
            raise TypeError("summary must be dict")
        if not isinstance(self.warnings, list):
            raise TypeError("warnings must be list")


@dataclass(frozen=True)
class AutomationTaskCreate:
    task_name: str
    business_unit: str
    brand_id: str
    brand_name: str
    platform: str
    channel: str
    file_type: str
    frequency: str
    scheduled_time: str
    date_window: str
    enabled: bool
    output_folder: str
    owner: str
    notes: str

    def __post_init__(self) -> None:
        for field_name, field_value in (
            ("task_name", self.task_name),
            ("business_unit", self.business_unit),
            ("brand_id", self.brand_id),
            ("brand_name", self.brand_name),
            ("platform", self.platform),
            ("channel", self.channel),
            ("file_type", self.file_type),
            ("frequency", self.frequency),
            ("scheduled_time", self.scheduled_time),
            ("date_window", self.date_window),
            ("output_folder", self.output_folder),
            ("owner", self.owner),
        ):
            if not isinstance(field_value, str) or not field_value.strip():
                raise ValueError(f"{field_name} must not be empty")
        if not isinstance(self.enabled, bool):
            raise TypeError("enabled must be bool")
        if not isinstance(self.notes, str):
            raise TypeError("notes must be str")


@dataclass(frozen=True)
class TaskRunCreate:
    task_id: int
    run_date: str
    status: str
    result_message: str
    error_message: str
    executed_by: str

    def __post_init__(self) -> None:
        if not isinstance(self.task_id, int) or self.task_id <= 0:
            raise ValueError("task_id must be positive int")
        for field_name, field_value in (
            ("run_date", self.run_date),
            ("status", self.status),
            ("executed_by", self.executed_by),
        ):
            if not isinstance(field_value, str) or not field_value.strip():
                raise ValueError(f"{field_name} must not be empty")
        if self.status not in TASK_STATUSES:
            raise ValueError("status must be pending, running, success, failed, or cancelled")
        for field_name, field_value in (
            ("result_message", self.result_message),
            ("error_message", self.error_message),
        ):
            if not isinstance(field_value, str):
                raise TypeError(f"{field_name} must be str")


@dataclass(frozen=True)
class FoundationCheckRecord:
    import_batch_id: str
    metadata: Any
    original_file_name: str
    stored_file_path: Path
    file_sha256: str
    recognized_file_type: str
    row_count: int
    status: str
    brand_match_score: int
    validation_errors: tuple[str, ...]
    validation_warnings: tuple[str, ...]

    def __post_init__(self) -> None:
        for field_name, field_value in (
            ("import_batch_id", self.import_batch_id),
            ("original_file_name", self.original_file_name),
            ("file_sha256", self.file_sha256),
            ("recognized_file_type", self.recognized_file_type),
            ("status", self.status),
        ):
            if not isinstance(field_value, str) or not field_value.strip():
                raise ValueError(f"{field_name} must not be empty")
        if not isinstance(self.stored_file_path, Path):
            raise TypeError("stored_file_path must be pathlib.Path")
        if not isinstance(self.row_count, int) or self.row_count < 0:
            raise ValueError("row_count must be non-negative int")
        if not isinstance(self.brand_match_score, int) or self.brand_match_score < 0:
            raise ValueError("brand_match_score must be non-negative int")
        if not isinstance(self.validation_errors, tuple):
            raise TypeError("validation_errors must be tuple")
        if not isinstance(self.validation_warnings, tuple):
            raise TypeError("validation_warnings must be tuple")


class UserRepository(ABC):
    @abstractmethod
    def create_user(self, request: UserCreate) -> UserRecord:
        raise NotImplementedError

    @abstractmethod
    def get_user(self, username: str) -> UserRecord | None:
        raise NotImplementedError

    @abstractmethod
    def verify_user(self, username: str, password: str) -> bool:
        raise NotImplementedError


class FoundationRepository(ABC):
    @abstractmethod
    def save_foundation_check(self, record: FoundationCheckRecord) -> None:
        raise NotImplementedError

    @abstractmethod
    def save_foundation_rows(self, import_batch_id: str, plan: Any) -> None:
        raise NotImplementedError

    @abstractmethod
    def query_foundation_rows(
        self,
        brand_id: str,
        platform: str,
        channel: str,
        file_type: str,
    ) -> list[dict[str, str]]:
        raise NotImplementedError


class ReportRepository(ABC):
    @abstractmethod
    def save_report(self, request: ReportCreate) -> int:
        raise NotImplementedError

    @abstractmethod
    def get_report(self, report_id: int) -> JobRecord | None:
        raise NotImplementedError


class TaskRepository(ABC):
    @abstractmethod
    def create_task(self, request: AutomationTaskCreate) -> int:
        raise NotImplementedError

    @abstractmethod
    def update_task_status(self, task_id: int, status: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_task(self, task_id: int) -> AutomationTaskRecord | None:
        raise NotImplementedError

    @abstractmethod
    def save_task_result(self, request: TaskRunCreate) -> int:
        raise NotImplementedError

    @abstractmethod
    def list_tasks(self) -> list[AutomationTaskRecord]:
        raise NotImplementedError

    @abstractmethod
    def list_task_runs(self, limit: int = 200) -> list[AutomationRunRecord]:
        raise NotImplementedError
