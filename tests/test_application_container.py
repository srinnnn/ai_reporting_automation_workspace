from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from backend.core.container import ApplicationContainer, build_application_container
from backend.repositories.interfaces import FoundationRepository, ReportRepository, TaskRepository, UserRepository
from backend.services.ai_content_service import AIContentService
from backend.services.data_foundation_service import DataFoundationService
from backend.services.report_service import ReportService
from backend.services.task_query_service import TaskQueryService
from backend.services.task_result_service import TaskResultService
from backend.services.task_service import TaskService
from backend.workers.contracts import TaskType
from backend.workers.executors.ai_content_executor import AIContentExecutor
from backend.workers.executors.data_import_executor import DataImportExecutor
from backend.workers.executors.report_executor import ReportExecutor
from backend.workers.task_runner import TaskRunner
from backend.workers.task_submitter import TaskSubmitter


class ApplicationContainerTests(unittest.TestCase):
    def test_application_container_can_be_created(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            container = _container(Path(temp_dir))
            try:
                self.assertIsInstance(container, ApplicationContainer)
                self.assertEqual(container.config.database.backend, "sqlite")
                self.assertEqual(container.logger.name, "ai_reporting_automation.container")
                self.assertFalse(hasattr(container, "get_everything"))
            finally:
                container.close()

    def test_repository_dependencies_are_assembled(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            container = _container(Path(temp_dir))
            try:
                self.assertIsInstance(container.repositories.users, UserRepository)
                self.assertIsInstance(container.repositories.foundation, FoundationRepository)
                self.assertIsInstance(container.repositories.reports, ReportRepository)
                self.assertIsInstance(container.repositories.tasks, TaskRepository)
            finally:
                container.close()

    def test_service_dependencies_are_assembled(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            container = _container(Path(temp_dir))
            try:
                self.assertIsInstance(container.services.data_foundation, DataFoundationService)
                self.assertIsInstance(container.services.reports, ReportService)
                self.assertIsInstance(container.services.ai_content, AIContentService)
                self.assertIsInstance(container.services.tasks, TaskService)
                self.assertIsInstance(container.services.task_query, TaskQueryService)
                self.assertIsInstance(container.services.task_result, TaskResultService)
            finally:
                container.close()

    def test_worker_dependencies_are_assembled(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            container = _container(Path(temp_dir))
            try:
                self.assertIsInstance(container.workers.data_import_executor, DataImportExecutor)
                self.assertIsInstance(container.workers.report_executor, ReportExecutor)
                self.assertIsInstance(container.workers.ai_content_executor, AIContentExecutor)
                self.assertIsInstance(container.workers.task_runner, TaskRunner)
                self.assertIsInstance(container.workers.task_submitter, TaskSubmitter)
                self.assertIn(TaskType.REPORT_GENERATE, container.workers.task_runner.executors)
            finally:
                container.close()

    def test_postgres_backend_fails_closed_without_connection(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            env = _env(Path(temp_dir))
            env["DATABASE_BACKEND"] = "postgres"
            env["DATABASE_URL"] = "postgresql://user:pass@example.invalid/db"

            with self.assertRaises(NotImplementedError):
                build_application_container(environ=env, root_dir=Path(temp_dir))


def _container(root: Path) -> ApplicationContainer:
    container = build_application_container(environ=_env(root), root_dir=root)
    assert isinstance(container, ApplicationContainer)
    return container


def _env(root: Path) -> dict[str, str]:
    if not isinstance(root, Path):
        raise TypeError("root must be pathlib.Path")
    runtime = root / "runtime"
    result = {
        "APP_ENV": "testing",
        "DATABASE_BACKEND": "sqlite",
        "SQLITE_PATH": str(runtime / "test.sqlite3"),
        "RUNTIME_DIR": str(runtime),
        "UPLOAD_DIR": str(runtime / "uploads"),
        "RESULT_DIR": str(runtime / "results"),
        "LOG_DIR": str(runtime / "logs"),
        "TEMPLATE_ROOT": str(root / "templates"),
        "REPORT_TASK_MODE": "legacy",
    }
    assert result["DATABASE_BACKEND"] == "sqlite"
    return result


if __name__ == "__main__":
    unittest.main()