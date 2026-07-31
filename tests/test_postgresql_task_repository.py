from __future__ import annotations

import inspect
import tempfile
import unittest
from pathlib import Path

from backend.repositories.interfaces import AutomationTaskCreate, TaskRepository, TaskRunCreate
from backend.repositories.postgresql import (
    PostgreSQLConnectionConfig,
    PostgreSQLConnectionProvider,
    PostgreSQLTaskRepository,
)
from backend.repositories.sqlite.task_repository import SQLiteTaskRepository
from intranet_app.storage import AppStorage, AutomationRunRecord, AutomationTaskRecord


class PostgreSQLTaskRepositorySkeletonTests(unittest.TestCase):
    def test_repository_inherits_task_repository(self) -> None:
        repository = _repository()

        self.assertTrue(issubclass(PostgreSQLTaskRepository, TaskRepository))
        self.assertIsInstance(repository, TaskRepository)

    def test_required_methods_exist(self) -> None:
        repository = _repository()

        for method_name in (
            "create_task",
            "update_task_status",
            "get_task",
            "save_task_result",
            "list_tasks",
            "list_task_runs",
        ):
            self.assertTrue(callable(getattr(repository, method_name)))

    def test_method_signatures_match_task_repository_contract(self) -> None:
        for method_name in (
            "create_task",
            "update_task_status",
            "get_task",
            "save_task_result",
            "list_tasks",
            "list_task_runs",
        ):
            expected = inspect.signature(getattr(TaskRepository, method_name))
            actual = inspect.signature(getattr(PostgreSQLTaskRepository, method_name))
            self.assertEqual(list(actual.parameters), list(expected.parameters))
            self.assertEqual(actual.return_annotation, expected.return_annotation)

    def test_read_methods_can_return_fixture_without_database_connection(self) -> None:
        task = _task(1)
        run = _run(10, 1)
        repository = _repository(fixture_tasks=(task,), fixture_runs=(run,))

        self.assertEqual(repository.get_task(1), task)
        self.assertIsNone(repository.get_task(2))
        self.assertEqual(repository.list_tasks(), [task])
        self.assertEqual(repository.list_task_runs(), [run])

    def test_write_methods_fail_closed_until_implemented(self) -> None:
        repository = _repository()

        with self.assertRaises(NotImplementedError):
            repository.create_task(_task_create())
        with self.assertRaises(NotImplementedError):
            repository.update_task_status(1, "running")
        with self.assertRaises(NotImplementedError):
            repository.save_task_result(_task_run_create())

    def test_connection_provider_does_not_connect_in_skeleton(self) -> None:
        provider = _provider()

        with self.assertRaises(NotImplementedError):
            provider.connection()
        with self.assertRaises(NotImplementedError):
            provider.transaction()

    def test_sqlite_adapter_still_initializes_and_updates_task(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = AppStorage(Path(temp_dir) / "runtime" / "test.sqlite3")
            storage.initialize("test-password")
            repository = SQLiteTaskRepository(storage)

            task_id = repository.create_task(_task_create())
            repository.update_task_status(task_id, "disabled")
            task = repository.get_task(task_id)

            self.assertIsNotNone(task)
            self.assertFalse(task.enabled)


def _repository(
    fixture_tasks: tuple[AutomationTaskRecord, ...] = (),
    fixture_runs: tuple[AutomationRunRecord, ...] = (),
) -> PostgreSQLTaskRepository:
    return PostgreSQLTaskRepository(_provider(), fixture_tasks=fixture_tasks, fixture_runs=fixture_runs)


def _provider() -> PostgreSQLConnectionProvider:
    return PostgreSQLConnectionProvider(PostgreSQLConnectionConfig("postgresql://user:password@localhost:5432/app"))


def _task(task_id: int) -> AutomationTaskRecord:
    return AutomationTaskRecord(
        id=task_id,
        task_name=f"task-{task_id}",
        business_unit="anta_retail_team",
        brand_id="anta_kids",
        brand_name="Anta Kids",
        platform="meituan",
        channel="instant_retail",
        file_type="REPORT_GENERATE",
        frequency="daily",
        scheduled_time="09:30",
        date_window="20260725",
        enabled=True,
        output_folder="runtime/results",
        owner="admin",
        notes="postgresql skeleton fixture",
        created_at="2026-07-31T13:30:00+08:00",
        updated_at="2026-07-31T13:31:00+08:00",
    )


def _run(run_id: int, task_id: int) -> AutomationRunRecord:
    return AutomationRunRecord(
        id=run_id,
        task_id=task_id,
        task_name=f"task-{task_id}",
        run_date="20260725",
        status="success",
        downloaded_file_count=0,
        synced_file_count=0,
        message="{}",
        executed_by="admin",
        created_at="2026-07-31T13:32:00+08:00",
    )


def _task_create() -> AutomationTaskCreate:
    return AutomationTaskCreate(
        task_name="postgresql skeleton task",
        business_unit="anta_retail_team",
        brand_id="anta_kids",
        brand_name="Anta Kids",
        platform="meituan",
        channel="instant_retail",
        file_type="REPORT_GENERATE",
        frequency="daily",
        scheduled_time="09:30",
        date_window="20260725",
        enabled=True,
        output_folder="runtime/results",
        owner="admin",
        notes="postgresql skeleton",
    )


def _task_run_create() -> TaskRunCreate:
    return TaskRunCreate(
        task_id=1,
        run_date="20260725",
        status="success",
        result_message="{}",
        error_message="",
        executed_by="admin",
    )


if __name__ == "__main__":
    unittest.main()
