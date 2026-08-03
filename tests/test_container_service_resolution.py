from __future__ import annotations

import io
import json
import tempfile
import unittest
from pathlib import Path

from backend.core.container import build_application_container
from backend.services.permission_service import PermissionService
from backend.services.task_query_service import TaskQueryService
from backend.services.task_result_service import TaskResultService
from intranet_app.app import IntranetApp, create_intranet_app
from intranet_app.auth import PasswordHash
from intranet_app.config import AppConfig
from intranet_app.storage import UserRecord


class ContainerServiceResolutionTests(unittest.TestCase):
    def test_container_services_are_resolved_first(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "materials").mkdir()
            container = build_application_container(environ=_env(root), root_dir=root)
            app = create_intranet_app(_config(root), container)
            try:
                self.assertIs(app._task_query_service(), container.services.task_query)
                self.assertIs(app._task_result_service(), container.services.task_result)
                self.assertIs(app._permission_service(), container.services.permissions)
            finally:
                app.close()

    def test_legacy_fallback_still_resolves_services_without_container(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "materials").mkdir()
            app = IntranetApp(_config(root))

            self.assertIsInstance(app._task_query_service(), TaskQueryService)
            self.assertIsInstance(app._task_result_service(), TaskResultService)
            self.assertIsInstance(app._permission_service(), PermissionService)

    def test_tasks_page_logic_still_renders_with_container_services(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "materials").mkdir()
            app = create_intranet_app(_config(root), build_application_container(environ=_env(root), root_dir=root))
            try:
                app.initialize()
                page = app._tasks_page(_user())

                self.assertIn("/tasks", page)
                self.assertIn("<table>", page)
            finally:
                app.close()

    def test_task_api_query_uses_container_services_and_keeps_missing_task_404(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "materials").mkdir()
            app = create_intranet_app(_config(root), build_application_container(environ=_env(root), root_dir=root))
            handler = _JsonHandler()
            try:
                app.initialize()
                app._handle_task_api_get(handler, "/api/tasks/999", _user())

                self.assertEqual(handler.status, 404)
                self.assertEqual(handler.json_body(), {"error": "999"})
            finally:
                app.close()


def _config(root: Path) -> AppConfig:
    if not isinstance(root, Path):
        raise TypeError("root must be pathlib.Path")
    return AppConfig(
        host="127.0.0.1",
        port=8765,
        secret_key="test-secret",
        database_path=root / "runtime" / "intranet.sqlite3",
        upload_dir=root / "runtime" / "uploads",
        result_dir=root / "runtime" / "results",
        template_root=root / "materials",
        default_admin_password="admin123",
    )


def _env(root: Path) -> dict[str, str]:
    if not isinstance(root, Path):
        raise TypeError("root must be pathlib.Path")
    runtime = root / "runtime"
    result = {
        "APP_ENV": "testing",
        "DATABASE_BACKEND": "sqlite",
        "SQLITE_PATH": str(runtime / "intranet.sqlite3"),
        "RUNTIME_DIR": str(runtime),
        "UPLOAD_DIR": str(runtime / "uploads"),
        "RESULT_DIR": str(runtime / "results"),
        "LOG_DIR": str(runtime / "logs"),
        "TEMPLATE_ROOT": str(root / "materials"),
        "REPORT_TASK_MODE": "legacy",
    }
    assert result["DATABASE_BACKEND"] == "sqlite"
    return result


def _user() -> UserRecord:
    return UserRecord(
        id=1,
        username="admin",
        display_name="Admin",
        role="admin",
        password_hash=PasswordHash("salt", "digest"),
    )


class _JsonHandler:
    def __init__(self) -> None:
        self.headers = {"Content-Length": "0"}
        self.rfile = io.BytesIO()
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


if __name__ == "__main__":
    unittest.main()
