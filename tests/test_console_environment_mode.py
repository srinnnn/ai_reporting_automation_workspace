from __future__ import annotations

import io
import json
import tempfile
import unittest
from pathlib import Path

from backend.core.container import build_application_container
from backend.services.permission_service import PermissionService
from intranet_app.app import IntranetApp
from intranet_app.auth import PasswordHash
from intranet_app.storage import UserRecord


class ConsoleEnvironmentModeTests(unittest.TestCase):
    def test_environment_config_api_returns_legacy_mode(self) -> None:
        payload = _config_payload("legacy")

        self.assertEqual(payload["report_task_mode"], "legacy")
        self.assertNotIn("secret-value", str(payload))
        self.assertNotIn("admin-password", str(payload))
        self.assertNotIn("api-key-value", str(payload))

    def test_environment_config_api_returns_task_mode(self) -> None:
        payload = _config_payload("task")

        self.assertEqual(payload["report_task_mode"], "task")
        self.assertEqual(payload["app_env"], "testing")
        self.assertEqual(payload["database_backend"], "sqlite")
        self.assertIn("storage", payload)

    def test_environment_page_loads_report_task_mode_from_safe_config_api(self) -> None:
        app = object.__new__(IntranetApp)

        page = app._console_environment_page(_user())

        self.assertIn("/api/system/config/status", page)
        self.assertIn("REPORT_TASK_MODE", page)
        self.assertIn("data.report_task_mode", page)
        self.assertNotIn("SECRET_KEY", page)
        self.assertNotIn("ADMIN_PASSWORD", page)
        self.assertNotIn("DASHSCOPE_API_KEY", page)
        self.assertNotIn("TOKEN", page)


def _config_payload(report_task_mode: str) -> dict[str, object]:
    with tempfile.TemporaryDirectory() as temp_dir:
        app = object.__new__(IntranetApp)
        app.container = _container(temp_dir, report_task_mode)
        app._permission_service = lambda: PermissionService()
        handler = _JsonHandler()
        try:
            app._handle_system_config_status_api(handler, _user())
        finally:
            app.container.close()

    if handler.status != 200:
        raise AssertionError(f"unexpected status: {handler.status}")
    body = handler.json_body()
    if not isinstance(body, dict):
        raise AssertionError("config payload must be object")
    return body


def _container(temp_dir: str, report_task_mode: str):
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
            "REPORT_TASK_MODE": report_task_mode,
            "AI_PROVIDER": "bailian",
            "BAILIAN_MODEL": "qwen-plus",
            "DASHSCOPE_API_KEY": "api-key-value",
            "INTRANET_SECRET_KEY": "secret-value",
            "INTRANET_ADMIN_PASSWORD": "admin-password",
        },
        root_dir=root,
    )


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
        payload = self.wfile.getvalue().decode("utf-8")
        if not payload:
            raise AssertionError("response body must not be empty")
        parsed = json.loads(payload)
        if not isinstance(parsed, dict):
            raise AssertionError("response must be json object")
        return parsed


if __name__ == "__main__":
    unittest.main()
