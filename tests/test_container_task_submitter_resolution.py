from __future__ import annotations

import io
import json
import tempfile
import unittest
from pathlib import Path

from backend.core.container import build_application_container
from backend.workers.contracts import TaskType, WorkerTaskStatus
from backend.workers.task_submitter import TaskSubmitter
from intranet_app.app import IntranetApp, create_intranet_app
from intranet_app.auth import PasswordHash
from intranet_app.config import AppConfig
from intranet_app.storage import UserRecord


class ContainerTaskSubmitterResolutionTests(unittest.TestCase):
    def test_container_mode_submitter_is_resolved_and_submits_successfully(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "materials").mkdir()
            app = create_intranet_app(_config(root), build_application_container(environ=_env(root), root_dir=root))
            try:
                app.initialize()
                submitter = app._task_submitter()
                result = submitter.submit(TaskType.REPORT_GENERATE, _payload(root)["payload"], "admin")

                self.assertIs(submitter, app.container.services.task_submitter)
                self.assertEqual(result.status, WorkerTaskStatus.FAILED)
                self.assertGreater(result.task_id, 0)
            finally:
                app.close()

    def test_legacy_fallback_still_returns_submitter_without_container(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "materials").mkdir()
            app = IntranetApp(_config(root))
            app.initialize()

            submitter = app._task_submitter()

            self.assertIsInstance(submitter, TaskSubmitter)

    def test_task_submit_api_uses_container_submitter_and_keeps_response_shape(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "materials").mkdir()
            app = create_intranet_app(_config(root), build_application_container(environ=_env(root), root_dir=root))
            handler = _JsonHandler(_payload(root))
            try:
                app.initialize()
                app._handle_task_api_submit(handler, _user())

                body = handler.json_body()
                self.assertEqual(handler.status, 200)
                self.assertIn("task_id", body)
                self.assertIn("status", body)
                self.assertGreater(int(body["task_id"]), 0)
            finally:
                app.close()


def _payload(root: Path) -> dict[str, object]:
    return {
        "task_type": "REPORT_GENERATE",
        "payload": {
            "task_name": "Anta daily report",
            "business_unit": "anta_retail_team",
            "brand_id": "anta_kids",
            "brand_name": "Anta Kids",
            "platform": "meituan",
            "channel": "instant_retail",
            "report_period": "daily",
            "report_date": "20260725",
            "date_window": "20260725",
            "output_folder": str(root / "runtime" / "results"),
        },
        "created_by": "admin",
    }


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
    def __init__(self, payload: dict[str, object]) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.headers = {"Content-Length": str(len(data))}
        self.rfile = io.BytesIO(data)
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