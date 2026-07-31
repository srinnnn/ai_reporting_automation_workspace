from __future__ import annotations

from intranet_app.storage import AutomationRunRecord, AutomationTaskRecord

from ..interfaces import AutomationTaskCreate, TASK_STATUSES, TaskRepository, TaskRunCreate
from .connection import PostgreSQLConnectionProvider


class PostgreSQLTaskRepository(TaskRepository):
    def __init__(
        self,
        connection_provider: PostgreSQLConnectionProvider,
        fixture_tasks: tuple[AutomationTaskRecord, ...] = (),
        fixture_runs: tuple[AutomationRunRecord, ...] = (),
    ) -> None:
        if not isinstance(connection_provider, PostgreSQLConnectionProvider):
            raise TypeError("connection_provider must be PostgreSQLConnectionProvider")
        if not isinstance(fixture_tasks, tuple):
            raise TypeError("fixture_tasks must be tuple")
        if not isinstance(fixture_runs, tuple):
            raise TypeError("fixture_runs must be tuple")
        for task in fixture_tasks:
            if not isinstance(task, AutomationTaskRecord):
                raise TypeError("fixture_tasks must contain AutomationTaskRecord")
        for run in fixture_runs:
            if not isinstance(run, AutomationRunRecord):
                raise TypeError("fixture_runs must contain AutomationRunRecord")
        self._connection_provider = connection_provider
        self._fixture_tasks = fixture_tasks
        self._fixture_runs = fixture_runs

    @property
    def connection_provider(self) -> PostgreSQLConnectionProvider:
        return self._connection_provider

    def create_task(self, request: AutomationTaskCreate) -> int:
        if not isinstance(request, AutomationTaskCreate):
            raise TypeError("request must be AutomationTaskCreate")
        raise NotImplementedError("PostgreSQLTaskRepository.create_task is a skeleton and does not write data")

    def update_task_status(self, task_id: int, status: str) -> None:
        if not isinstance(task_id, int) or task_id <= 0:
            raise ValueError("task_id must be positive int")
        if not isinstance(status, str) or not status.strip():
            raise ValueError("status must not be empty")
        if status.strip().lower() not in TASK_STATUSES and status.strip().lower() not in {"enabled", "disabled"}:
            raise ValueError("task status must be enabled, disabled, pending, running, success, failed, or cancelled")
        raise NotImplementedError("PostgreSQLTaskRepository.update_task_status is a skeleton and does not write data")

    def get_task(self, task_id: int) -> AutomationTaskRecord | None:
        if not isinstance(task_id, int) or task_id <= 0:
            raise ValueError("task_id must be positive int")
        for task in self._fixture_tasks:
            if task.id == task_id:
                return task
        return None

    def save_task_result(self, request: TaskRunCreate) -> int:
        if not isinstance(request, TaskRunCreate):
            raise TypeError("request must be TaskRunCreate")
        raise NotImplementedError("PostgreSQLTaskRepository.save_task_result is a skeleton and does not write data")

    def list_tasks(self) -> list[AutomationTaskRecord]:
        result = list(self._fixture_tasks)
        assert isinstance(result, list)
        return result

    def list_task_runs(self, limit: int = 200) -> list[AutomationRunRecord]:
        if not isinstance(limit, int) or limit <= 0:
            raise ValueError("limit must be positive int")
        result = list(self._fixture_runs[:limit])
        assert isinstance(result, list)
        return result
