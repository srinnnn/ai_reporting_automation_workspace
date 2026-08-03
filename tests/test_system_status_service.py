from __future__ import annotations

import io
import json
import tempfile
import unittest
from pathlib import Path

from backend.core.container import build_application_container
from backend.services.permission_service import PermissionService
from backend.services.system_status_service import SystemStatusService
from intranet_app.app import IntranetApp
from intranet_app.auth import PasswordHash
from intranet_app.storage import UserRecord


class SystemStatusServiceTests(unittest.TestCase):
    def test_admin_can_read_health_without_secret_values(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = _service(temp_dir, api_key="sk-test-secret")
            try:
                payload = service.get_health_status(_user(role="admin"))
            finally:
                service.container.close()

        self.assertIn("components", payload)
        self.assertNotIn("sk-test-secret", str(payload))
        self.assertNotIn("password", str(payload).lower())

    def test_developer_can_read_safe_config_status(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = _service(temp_dir, api_key="sk-test-secret")
            try:
                payload = service.get_config_status(_user(role="developer"))
            finally:
                service.container.close()

        self.assertEqual(payload["app_env"], "testing")
        self.assertEqual(payload["database_backend"], "sqlite")
        self.assertEqual(payload["report_task_mode"], "legacy")
        self.assertEqual(payload["ai_provider"], "bailian")
        self.assertEqual(payload["ai_model"], "qwen-plus")
        self.assertTrue(payload["ai_api_key_configured"])
        self.assertIn("storage", payload)
        self.assertNotIn("sk-test-secret", str(payload))
        self.assertNotIn("INTRANET_SECRET_KEY", str(payload))
        self.assertNotIn("INTRANET_ADMIN_PASSWORD", str(payload))

    def test_business_owner_is_forbidden(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = _service(temp_dir)
            try:
                with self.assertRaises(PermissionError):
                    service.get_config_status(_user(role="business_owner"))
            finally:
                service.container.close()

    def test_viewer_is_forbidden(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = _service(temp_dir)
            try:
                with self.assertRaises(PermissionError):
                    service.get_health_status(_user(role="viewer"))
            finally:
                service.container.close()

    def test_api_health_allows_admin(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            app = object.__new__(IntranetApp)
            app.container = _container(temp_dir)
            app._permission_service = lambda: PermissionService()
            handler = _JsonHandler()
            try:
                app._handle_system_health_api(handler, _user(role="admin"))
            finally:
                app.container.close()

        self.assertEqual(handler.status, 200)
        self.assertIn("components", handler.json_body())

    def test_api_config_denies_viewer(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            app = object.__new__(IntranetApp)
            app.container = _container(temp_dir)
            app._permission_service = lambda: PermissionService()
            handler = _JsonHandler()
            try:
                app._handle_system_config_status_api(handler, _user(role="viewer"))
            finally:
                app.container.close()

        self.assertEqual(handler.status, 403)
        self.assertEqual(handler.json_body(), {"error": "forbidden"})


def _service(temp_dir: str, api_key: str = "") -> SystemStatusService:
    return SystemStatusService(_container(temp_dir, api_key), PermissionService())


def _container(temp_dir: str, api_key: str = ""):
    root = Path(temp_dir)
    runtime = root / "runtime"
    upload = runtime / "uploads"
    result = runtime / "results"
    log = runtime / "logs"
    for path in (upload, result, log):
        path.mkdir(parents=True, exist_ok=True)
    return build_application_container(
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
            "DASHSCOPE_API_KEY": api_key,
        },
        root_dir=root,
    )


def _user(username: str = "admin", role: str = "admin") -> UserRecord:
    return UserRecord(
        id=1,
        username=username,
        display_name=username.title(),
        role=role,
        password_hash=PasswordHash("salt", "digest"),
    )


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


if __name__ == "__main__":
    unittest.main()