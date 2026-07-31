from __future__ import annotations

from intranet_app.storage import AppStorage, AutomationRunRecord, AutomationTaskRecord

from ..interfaces import AutomationTaskCreate, TASK_STATUSES, TaskRepository, TaskRunCreate


class SQLiteTaskRepository(TaskRepository):
    def __init__(self, storage: AppStorage) -> None:
        if not isinstance(storage, AppStorage):
            raise TypeError("storage must be AppStorage")
        self._storage = storage

    def create_task(self, request: AutomationTaskCreate) -> int:
        if not isinstance(request, AutomationTaskCreate):
            raise TypeError("request must be AutomationTaskCreate")
        task_id = self._storage.save_automation_task(
            task_name=request.task_name,
            business_unit=request.business_unit,
            brand_id=request.brand_id,
            brand_name=request.brand_name,
            platform=request.platform,
            channel=request.channel,
            file_type=request.file_type,
            frequency=request.frequency,
            scheduled_time=request.scheduled_time,
            date_window=request.date_window,
            enabled=request.enabled,
            output_folder=request.output_folder,
            owner=request.owner,
            notes=request.notes,
        )
        assert task_id > 0
        return task_id

    def update_task_status(self, task_id: int, status: str) -> None:
        if not isinstance(task_id, int) or task_id <= 0:
            raise ValueError("task_id must be positive int")
        if not isinstance(status, str) or not status.strip():
            raise ValueError("status must not be empty")
        normalized = status.strip().lower()
        if normalized == "enabled":
            self._storage.set_automation_task_enabled(task_id, True)
            return
        if normalized == "disabled":
            self._storage.set_automation_task_enabled(task_id, False)
            return
        if normalized in TASK_STATUSES:
            self._storage.save_automation_run(
                task_id=task_id,
                run_date="system",
                status=normalized,
                downloaded_file_count=0,
                synced_file_count=0,
                message=f"task status changed to {normalized}",
                executed_by="system",
            )
            return
        raise ValueError("task status must be enabled, disabled, pending, running, success, failed, or cancelled")

    def get_task(self, task_id: int) -> AutomationTaskRecord | None:
        if not isinstance(task_id, int) or task_id <= 0:
            raise ValueError("task_id must be positive int")
        return self._storage.get_automation_task(task_id)

    def save_task_result(self, request: TaskRunCreate) -> int:
        if not isinstance(request, TaskRunCreate):
            raise TypeError("request must be TaskRunCreate")
        message = _build_run_message(request.result_message, request.error_message)
        run_id = self._storage.save_automation_run(
            task_id=request.task_id,
            run_date=request.run_date,
            status=request.status,
            downloaded_file_count=0,
            synced_file_count=0,
            message=message,
            executed_by=request.executed_by,
        )
        assert run_id > 0
        return run_id

    def list_tasks(self) -> list[AutomationTaskRecord]:
        result = self._storage.list_automation_tasks()
        assert isinstance(result, list)
        return result

    def list_task_runs(self, limit: int = 200) -> list[AutomationRunRecord]:
        if not isinstance(limit, int) or limit <= 0:
            raise ValueError("limit must be positive int")
        result = self._storage.list_automation_runs(limit)
        assert isinstance(result, list)
        return result


def _build_run_message(result_message: str, error_message: str) -> str:
    if not isinstance(result_message, str):
        raise TypeError("result_message must be str")
    if not isinstance(error_message, str):
        raise TypeError("error_message must be str")
    if error_message.strip():
        return f"error: {error_message.strip()}"
    if result_message.strip():
        return result_message.strip()
    return "no result message"
