from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from backend.repositories.sqlite.task_repository import SQLiteTaskRepository
from backend.services.task_service import TaskCreateRequest, TaskResultSaveRequest, TaskService, TaskStatus, TaskStatusUpdate
from intranet_app.storage import AppStorage


class TaskServiceTests(unittest.TestCase):
    def test_create_task(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            storage = _storage(Path(tmp_dir))
            service = TaskService(SQLiteTaskRepository(storage))

            task_id = service.create_task(_task_request())
            task = service.get_task(task_id)

            self.assertIsNotNone(task)
            self.assertEqual(task.task_name, "Anta Meituan Daily")
            self.assertEqual(task.file_type, "p1_daily_report")

    def test_update_task_status_records_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            storage = _storage(Path(tmp_dir))
            service = TaskService(SQLiteTaskRepository(storage))
            task_id = service.create_task(_task_request())

            run_id = service.update_task_status(
                TaskStatusUpdate(
                    task_id=task_id,
                    status=TaskStatus.RUNNING,
                    run_date="20260725",
                    result_message="started",
                    executed_by="admin",
                )
            )
            runs = storage.list_automation_runs()

            self.assertGreater(run_id, 0)
            self.assertEqual(runs[0].status, "running")
            self.assertEqual(runs[0].message, "started")

    def test_get_task_returns_none_for_missing_task(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            storage = _storage(Path(tmp_dir))
            service = TaskService(SQLiteTaskRepository(storage))

            task = service.get_task(999)

            self.assertIsNone(task)

    def test_failed_task_records_error_message(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            storage = _storage(Path(tmp_dir))
            service = TaskService(SQLiteTaskRepository(storage))
            task_id = service.create_task(_task_request())

            run_id = service.save_task_result(
                TaskResultSaveRequest(
                    task_id=task_id,
                    status=TaskStatus.FAILED,
                    run_date="20260725",
                    result_message="",
                    error_message="foundation data missing",
                    executed_by="admin",
                )
            )
            runs = storage.list_automation_runs()

            self.assertGreater(run_id, 0)
            self.assertEqual(runs[0].status, "failed")
            self.assertEqual(runs[0].message, "error: foundation data missing")

    def test_failed_task_requires_error_message(self) -> None:
        with self.assertRaisesRegex(ValueError, "error_message"):
            TaskResultSaveRequest(
                task_id=1,
                status=TaskStatus.FAILED,
                run_date="20260725",
                result_message="",
                error_message="",
                executed_by="admin",
            )


def _storage(root: Path) -> AppStorage:
    storage = AppStorage(root / "runtime" / "test.sqlite3")
    storage.initialize("test-password")
    return storage


def _task_request() -> TaskCreateRequest:
    return TaskCreateRequest(
        task_name="Anta Meituan Daily",
        business_unit="anta_retail_team",
        brand_id="anta_kids",
        brand_name="Anta Kids",
        platform="meituan",
        channel="instant_retail",
        task_type="p1_daily_report",
        frequency="daily",
        scheduled_time="09:30",
        date_window="yesterday",
        output_folder="runtime/results",
        owner="admin",
        notes="service test",
    )


if __name__ == "__main__":
    unittest.main()
