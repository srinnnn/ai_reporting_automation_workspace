from __future__ import annotations

import io
import json
import tempfile
import unittest
from pathlib import Path

from backend.core.container import build_application_container
from backend.repositories.interfaces import AutomationTaskCreate, TaskRepository, TaskRunCreate
from backend.services.dashboard_service import DashboardService
from backend.services.permission_service import PermissionService
from backend.services.system_status_service import SystemStatusService
from backend.services.task_query_service import TaskQueryService
from intranet_app.app import IntranetApp
from intranet_app.auth import PasswordHash
from intranet_app.storage import AutomationRunRecord, AutomationTaskRecord, UserRecord


class DashboardApiTests(unittest.TestCase):
    def test_dashboard_api_returns_admin_payload(self) -> None:
        app = object.__new__(IntranetApp)
        app._dashboard_service = lambda: _DashboardService(
            payload={
                "system_status": {"application": {"status": "ok"}},
                "task_summary": {"total": 1, "pending": 0, "running": 0, "success": 1, "failed": 0},
                "recent_failed_tasks": [],
            }
        )
        handler = _JsonHandler()

        app._handle_console_dashboard_api(handler, _user(role="admin"))

        body = handler.json_body()
        self.assertEqual(handler.status, 200)
        self.assertEqual(body["task_summary"]["total"], 1)
        self.assertIn("system_status", body)

    def test_dashboard_api_denies_viewer(self) -> None:
        app = object.__new__(IntranetApp)
        app._dashboard_service = lambda: _DashboardService(error=PermissionError("forbidden"))
        handler = _JsonHandler()

        app._handle_console_dashboard_api(handler, _user(role="viewer"))

        self.assertEqual(handler.status, 403)
        self.assertEqual(handler.json_body(), {"error": "forbidden"})


class DashboardServiceTests(unittest.TestCase):
    def test_admin_dashboard_contains_system_status_and_failed_tasks(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = _real_dashboard_service(temp_dir)
            try:
                payload = service.get_dashboard(_user(role="admin"))
            finally:
                service.system_status.container.close()

        self.assertIn("application", payload["system_status"])
        self.assertEqual(payload["task_summary"], {"total": 3, "pending": 1, "running": 0, "success": 1, "failed": 1})
        self.assertEqual(payload["recent_failed_tasks"][0]["task_id"], 2)
        self.assertEqual(payload["recent_failed_tasks"][0]["error"], "download failed")

    def test_developer_dashboard_is_complete(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = _real_dashboard_service(temp_dir)
            try:
                payload = service.get_dashboard(_user(username="dev", role="developer"))
            finally:
                service.system_status.container.close()

        self.assertIn("database", payload["system_status"])
        self.assertEqual(payload["task_summary"]["total"], 3)

    def test_business_owner_dashboard_only_returns_scoped_task_info(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = _real_dashboard_service(temp_dir)
            try:
                payload = service.get_dashboard(_user(username="owner", role="business_owner|brand_id=anta"))
            finally:
                service.system_status.container.close()

        self.assertEqual(payload["system_status"], {"available": False, "reason": "business_scope_only"})
        self.assertEqual(payload["task_summary"]["total"], 2)
        self.assertEqual(payload["task_summary"]["failed"], 1)
        self.assertEqual([item["task_id"] for item in payload["recent_failed_tasks"]], [2])

    def test_viewer_dashboard_is_forbidden(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = _real_dashboard_service(temp_dir)
            try:
                with self.assertRaises(PermissionError):
                    service.get_dashboard(_user(username="viewer", role="viewer"))
            finally:
                service.system_status.container.close()


def _real_dashboard_service(temp_dir: str) -> DashboardService:
    query = TaskQueryService(_MemoryTaskRepository())
    return DashboardService(_system_status_service(temp_dir), query, PermissionService())


def _system_status_service(temp_dir: str) -> SystemStatusService:
    root = Path(temp_dir)
    runtime = root / "runtime"
    upload = runtime / "uploads"
    result = runtime / "results"
    log = runtime / "logs"
    for path in (upload, result, log):
        path.mkdir(parents=True, exist_ok=True)
    container = build_application_container(
        environ={
            "APP_ENV": "testing",
            "DATABASE_BACKEND": "sqlite",
            "SQLITE_PATH": str(runtime / "test.sqlite3"),
            "RUNTIME_DIR": str(runtime),
            "UPLOAD_DIR": str(upload),
            "RESULT_DIR": str(result),
            "LOG_DIR": str(log),
            "REPORT_TASK_MODE": "legacy",
            "AI_PROVIDER": "bailian",
            "BAILIAN_MODEL": "qwen-plus",
        },
        root_dir=root,
    )
    return SystemStatusService(container, PermissionService())


class _MemoryTaskRepository(TaskRepository):
    def __init__(self) -> None:
        self.tasks = [
            _automation_task(1, "anta", "meituan", "alice", enabled=True),
            _automation_task(2, "anta", "meituan", "bob", enabled=True),
            _automation_task(3, "nike", "jd", "carol", enabled=True),
        ]
        self.runs = [
            _run(1, "success", '{"rows": 12}'),
            _run(2, "failed", "error: download failed"),
        ]

    def create_task(self, request: AutomationTaskCreate) -> int:
        raise NotImplementedError

    def update_task_status(self, task_id: int, status: str) -> None:
        raise NotImplementedError

    def get_task(self, task_id: int) -> AutomationTaskRecord | None:
        for task in self.tasks:
            if task.id == task_id:
                return task
        return None

    def save_task_result(self, request: TaskRunCreate) -> int:
        raise NotImplementedError

    def list_tasks(self) -> list[AutomationTaskRecord]:
        return list(self.tasks)

    def list_task_runs(self, limit: int = 200) -> list[AutomationRunRecord]:
        return list(self.runs[:limit])


class _DashboardService:
    def __init__(self, payload: dict[str, object] | None = None, error: Exception | None = None) -> None:
        self._payload = payload or {}
        self._error = error

    def get_dashboard(self, user: UserRecord) -> dict[str, object]:
        if self._error is not None:
            raise self._error
        return dict(self._payload)


class _JsonHandler:
    def __init__(self) -> None:
        self.wfile = io.BytesIO()
        self.status = 0
        self.headers_sent: list[tuple[str, str]] = []

    def send_response(self, status: int) -> None:
        self.status = status

    def send_header(self, name: str, value: str) -> None:
        self.headers_sent.append((name, value))

    def end_headers(self) -> None:
        return None

    def json_body(self) -> dict[str, object]:
        return json.loads(self.wfile.getvalue().decode("utf-8"))


def _automation_task(task_id: int, brand_id: str, platform: str, owner: str, enabled: bool) -> AutomationTaskRecord:
    return AutomationTaskRecord(
        id=task_id,
        task_name=f"Task {task_id}",
        business_unit="retail",
        brand_id=brand_id,
        brand_name=brand_id.title(),
        platform=platform,
        channel="instant_retail",
        file_type="REPORT_GENERATE",
        frequency="daily",
        scheduled_time="09:00",
        date_window="20260803",
        enabled=enabled,
        output_folder="runtime/results",
        owner=owner,
        notes="",
        created_at="2026-08-03T09:00:00+08:00",
        updated_at="2026-08-03T09:01:00+08:00",
    )


def _run(task_id: int, status: str, message: str) -> AutomationRunRecord:
    return AutomationRunRecord(
        id=task_id,
        task_id=task_id,
        task_name=f"Task {task_id}",
        run_date="20260803",
        status=status,
        downloaded_file_count=0,
        synced_file_count=0,
        message=message,
        executed_by="admin",
        created_at="2026-08-03T10:00:00+08:00",
    )


def _user(username: str = "admin", role: str = "admin") -> UserRecord:
    return UserRecord(
        id=1,
        username=username,
        display_name=username.title(),
        role=role,
        password_hash=PasswordHash("salt", "digest"),
    )


if __name__ == "__main__":
    unittest.main()