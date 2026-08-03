from __future__ import annotations

import io
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from backend.services.task_query_service import TaskReadModel
from backend.services.task_result_service import TaskDownloadInfo, TaskResultView
from backend.workers.contracts import TaskResult, WorkerTaskStatus
from intranet_app.app import IntranetApp
from intranet_app.auth import PasswordHash
from intranet_app.storage import UserRecord


class TaskApiTests(unittest.TestCase):
    def test_submit_task_returns_task_id_and_status(self) -> None:
        app = object.__new__(IntranetApp)
        with tempfile.TemporaryDirectory() as temp_dir:
            result_dir = Path(temp_dir) / "results"
            app.config = SimpleNamespace(result_dir=result_dir)
            submitter = _TaskSubmitter()
            app._task_submitter = lambda: submitter
            handler = _JsonHandler(
                {
                    "task_type": "REPORT_GENERATE",
                    "payload": {
                        "brand_id": "anta_kids",
                        "brand_name": "Anta Kids",
                        "platform": "meituan",
                        "channel": "instant_retail",
                        "report_period": "daily",
                        "report_date": "20260725",
                        "date_window": "20260725",
                        "business_unit": "anta_retail_team",
                    },
                    "created_by": "admin",
                }
            )

            app._handle_task_api_submit(handler, _user())

        self.assertEqual(handler.status, 200)
        self.assertEqual(handler.json_body(), {"status": "success", "task_id": 42})
        self.assertEqual(submitter.last_task_type, "REPORT_GENERATE")
        self.assertEqual(submitter.last_created_by, "admin")
        self.assertEqual(submitter.last_payload["output_folder"], str(result_dir))

    def test_viewer_submit_task_returns_403(self) -> None:
        app = object.__new__(IntranetApp)
        with tempfile.TemporaryDirectory() as temp_dir:
            app.config = SimpleNamespace(result_dir=Path(temp_dir) / "results")
            submitter = _TaskSubmitter()
            app._task_submitter = lambda: submitter
            handler = _JsonHandler(
                {
                    "task_type": "REPORT_GENERATE",
                    "payload": {"brand_id": "anta_kids"},
                    "created_by": "viewer",
                }
            )

            app._handle_task_api_submit(handler, _user("viewer", "viewer"))

        self.assertEqual(handler.status, 403)
        self.assertEqual(handler.json_body(), {"error": "forbidden"})
        self.assertEqual(submitter.last_task_type, "")

    def test_query_task_returns_safe_result_information(self) -> None:
        app = object.__new__(IntranetApp)
        app._task_console_service = lambda: _TaskConsoleService(
            detail={
                "task_id": 7,
                "filename": "daily.csv",
                "file_path": "task-results/7/daily.csv",
            }
        )
        handler = _JsonHandler()

        app._handle_task_api_get(handler, "/api/tasks/7", _user())

        body = handler.json_body()
        self.assertEqual(handler.status, 200)
        self.assertEqual(body["task_id"], 7)
        self.assertEqual(body["filename"], "daily.csv")
        self.assertEqual(body["file_path"], "task-results/7/daily.csv")
        self.assertNotIn("runtime", str(body))

    def test_query_task_forbidden_for_invisible_task(self) -> None:
        app = object.__new__(IntranetApp)
        app._task_console_service = lambda: _TaskConsoleService(error=PermissionError("forbidden"))
        handler = _JsonHandler()

        app._handle_task_api_get(handler, "/api/tasks/7", _user("alice", "operator"))

        self.assertEqual(handler.status, 403)
        self.assertEqual(handler.json_body(), {"error": "forbidden"})

    def test_download_task_result_streams_file(self) -> None:
        app = object.__new__(IntranetApp)
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "daily.csv"
            path.write_text("metric,value\nsales,100\n", encoding="utf-8")
            app._task_query_service = lambda: _TaskQueryService(_task(7, "success", {"result_asset": {"filename": "daily.csv"}}))
            app._task_result_service = lambda: _TaskResultService(download=TaskDownloadInfo(filename="daily.csv", path=path))
            handler = _JsonHandler()

            app._handle_task_api_download(handler, "/api/tasks/7/download", _user())

        self.assertEqual(handler.status, 200)
        self.assertIn(("Content-Disposition", "attachment; filename*=UTF-8''daily.csv"), handler.headers_sent)
        self.assertIn(b"sales,100", handler.wfile.getvalue())

    def test_download_missing_file_returns_json_404(self) -> None:
        app = object.__new__(IntranetApp)
        app._task_query_service = lambda: _TaskQueryService(_task(7, "success", {"result_asset": {"filename": "missing.csv"}}))
        app._task_result_service = lambda: _TaskResultService(error=FileNotFoundError("missing.csv"))
        handler = _JsonHandler()

        app._handle_task_api_download(handler, "/api/tasks/7/download", _user())

        self.assertEqual(handler.status, 404)
        self.assertEqual(handler.json_body(), {"error": "missing.csv"})


class _TaskConsoleService:
    def __init__(self, detail: dict[str, object] | None = None, error: Exception | None = None) -> None:
        self._detail = detail or {}
        self._error = error

    def get_task_detail(self, user: UserRecord, task_id: int) -> dict[str, object]:
        if self._error is not None:
            raise self._error
        return dict(self._detail)

    def list_visible_tasks(self, user: UserRecord, filters: object | None = None) -> dict[str, object]:
        return {"tasks": [], "total": 0}

class _TaskSubmitter:
    def __init__(self) -> None:
        self.last_task_type = ""
        self.last_payload: dict[str, object] = {}
        self.last_created_by = ""

    def submit(self, task_type, payload, created_by):
        self.last_task_type = str(task_type)
        self.last_payload = dict(payload)
        self.last_created_by = str(created_by)
        return TaskResult(
            task_id=42,
            status=WorkerTaskStatus.SUCCESS,
            result={},
            error="",
            finished_time="2026-07-31T09:40:00+08:00",
        )


class _TaskResultService:
    def __init__(
        self,
        view: TaskResultView | None = None,
        download: TaskDownloadInfo | None = None,
        error: Exception | None = None,
    ) -> None:
        self._view = view
        self._download = download
        self._error = error

    def get_result(self, task_id: int) -> TaskResultView:
        if self._error is not None:
            raise self._error
        if self._view is None:
            raise FileNotFoundError(str(task_id))
        return self._view

    def get_download_info(self, task_id: int) -> TaskDownloadInfo:
        if self._error is not None:
            raise self._error
        if self._download is None:
            raise FileNotFoundError(str(task_id))
        return self._download


class _TaskQueryService:
    def __init__(self, task: TaskReadModel | None) -> None:
        self._task = task

    def get_task(self, task_id: int) -> TaskReadModel | None:
        if self._task is None or self._task.task_id != task_id:
            return None
        return self._task


class _JsonHandler:
    def __init__(self, body: dict[str, object] | None = None) -> None:
        data = json.dumps(body or {}, ensure_ascii=False).encode("utf-8")
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


def _user(username: str = "admin", role: str = "admin") -> UserRecord:
    return UserRecord(
        id=1,
        username=username,
        display_name=username.title(),
        role=role,
        password_hash=PasswordHash("salt", "digest"),
    )


def _task(task_id: int, status: str, result: dict[str, object], created_by: str = "admin") -> TaskReadModel:
    return TaskReadModel(
        task_id=task_id,
        task_type="REPORT_GENERATE",
        status=status,
        created_by=created_by,
        created_time="2026-07-31T09:40:00+08:00",
        result=result,
        error="",
    )


if __name__ == "__main__":
    unittest.main()
