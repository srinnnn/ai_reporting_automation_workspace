from __future__ import annotations

import io
import json
import unittest

from backend.repositories.interfaces import AutomationTaskCreate, TaskRepository, TaskRunCreate
from backend.services.permission_service import PermissionService
from backend.services.task_console_service import TaskConsoleFilters, TaskConsoleService
from backend.services.task_query_service import TaskQueryService
from backend.services.task_result_service import TaskResultService
from intranet_app.app import IntranetApp
from intranet_app.auth import PasswordHash
from intranet_app.storage import AutomationRunRecord, AutomationTaskRecord, UserRecord


class TaskConsoleApiTests(unittest.TestCase):
    def test_list_tasks_passes_filters_to_console_service(self) -> None:
        app = object.__new__(IntranetApp)
        service = _TaskConsoleService(
            list_payload={
                "tasks": [
                    {
                        "task_id": 1,
                        "task_type": "REPORT_GENERATE",
                        "status": "success",
                        "created_by": "admin",
                        "brand_id": "anta",
                        "business_unit": "retail",
                        "platform": "meituan",
                        "channel": "instant_retail",
                    }
                ],
                "total": 1,
            }
        )
        app._task_console_service = lambda: service
        handler = _JsonHandler(path="/api/tasks?task_type=REPORT_GENERATE&status=success&brand_id=anta&platform=meituan")

        app._handle_task_api_list(handler, _user(role="developer"))

        body = handler.json_body()
        self.assertEqual(handler.status, 200)
        self.assertEqual(body["total"], 1)
        self.assertEqual(body["tasks"][0]["task_id"], 1)
        self.assertEqual(service.last_filters.task_type, "REPORT_GENERATE")
        self.assertEqual(service.last_filters.status, "success")
        self.assertEqual(service.last_filters.brand_id, "anta")
        self.assertEqual(service.last_filters.platform, "meituan")

    def test_task_detail_returns_safe_payload(self) -> None:
        app = object.__new__(IntranetApp)
        app._task_console_service = lambda: _TaskConsoleService(
            detail_payload={
                "task_id": 9,
                "task_type": "REPORT_GENERATE",
                "status": "success",
                "created_by": "admin",
                "created_time": "2026-08-03T10:00:00+08:00",
                "updated_at": "2026-08-03T10:01:00+08:00",
                "error": "",
                "result_summary": {"rows": 12},
                "result_asset": {"filename": "daily.csv", "size": 20},
                "filename": "daily.csv",
                "file_path": "task-results/9/daily.csv",
                "downloadable": True,
            }
        )
        handler = _JsonHandler(path="/api/tasks/9")

        app._handle_task_api_get(handler, "/api/tasks/9", _user(role="admin"))

        body = handler.json_body()
        self.assertEqual(handler.status, 200)
        self.assertEqual(body["task_id"], 9)
        self.assertEqual(body["filename"], "daily.csv")
        self.assertNotIn("runtime", str(body).lower())
        self.assertNotIn("secret", str(body).lower())

    def test_list_tasks_forbidden_returns_403(self) -> None:
        app = object.__new__(IntranetApp)
        app._task_console_service = lambda: _TaskConsoleService(error=PermissionError("forbidden"))
        handler = _JsonHandler(path="/api/tasks")

        app._handle_task_api_list(handler, _user(role="viewer"))

        self.assertEqual(handler.status, 403)
        self.assertEqual(handler.json_body(), {"error": "forbidden"})

    def test_task_detail_not_found_returns_404(self) -> None:
        app = object.__new__(IntranetApp)
        app._task_console_service = lambda: _TaskConsoleService(error=FileNotFoundError("404"))
        handler = _JsonHandler(path="/api/tasks/404")

        app._handle_task_api_get(handler, "/api/tasks/404", _user(role="admin"))

        self.assertEqual(handler.status, 404)
        self.assertEqual(handler.json_body(), {"error": "404"})


class TaskConsoleServiceTests(unittest.TestCase):
    def test_developer_can_view_all_tasks(self) -> None:
        service = _real_console_service()

        payload = service.list_visible_tasks(_user(username="dev", role="developer"))

        self.assertEqual(payload["total"], 2)
        self.assertEqual({item["task_id"] for item in payload["tasks"]}, {1, 2})

    def test_business_owner_only_sees_scope_tasks(self) -> None:
        service = _real_console_service()

        payload = service.list_visible_tasks(_user(username="owner", role="business_owner|brand_id=anta"))

        self.assertEqual(payload["total"], 1)
        self.assertEqual(payload["tasks"][0]["brand_id"], "anta")

    def test_extra_filters_apply_before_permission_filter(self) -> None:
        service = _real_console_service()

        payload = service.list_visible_tasks(
            _user(username="dev", role="developer"),
            TaskConsoleFilters(platform="jd"),
        )

        self.assertEqual(payload["total"], 1)
        self.assertEqual(payload["tasks"][0]["platform"], "jd")


class _MemoryTaskRepository(TaskRepository):
    def __init__(self) -> None:
        self.tasks = [
            _automation_task(1, "anta", "meituan", "alice"),
            _automation_task(2, "nike", "jd", "bob"),
        ]
        self.runs = [
            AutomationRunRecord(
                id=1,
                task_id=1,
                task_name="Anta Daily",
                run_date="20260803",
                status="success",
                downloaded_file_count=0,
                synced_file_count=0,
                message='{"rows": 12}',
                executed_by="alice",
                created_at="2026-08-03T10:00:00+08:00",
            )
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


def _real_console_service() -> TaskConsoleService:
    query = TaskQueryService(_MemoryTaskRepository())
    return TaskConsoleService(query, TaskResultService(query), PermissionService())


def _automation_task(task_id: int, brand_id: str, platform: str, owner: str) -> AutomationTaskRecord:
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
        enabled=True,
        output_folder="runtime/results",
        owner=owner,
        notes="",
        created_at="2026-08-03T09:00:00+08:00",
        updated_at="2026-08-03T09:01:00+08:00",
    )


class _TaskConsoleService:
    def __init__(
        self,
        list_payload: dict[str, object] | None = None,
        detail_payload: dict[str, object] | None = None,
        error: Exception | None = None,
    ) -> None:
        self._list_payload = list_payload or {"tasks": [], "total": 0}
        self._detail_payload = detail_payload or {}
        self._error = error
        self.last_filters = None

    def list_visible_tasks(self, user: UserRecord, filters) -> dict[str, object]:
        if self._error is not None:
            raise self._error
        self.last_filters = filters
        return dict(self._list_payload)

    def get_task_detail(self, user: UserRecord, task_id: int) -> dict[str, object]:
        if self._error is not None:
            raise self._error
        return dict(self._detail_payload)


class _JsonHandler:
    def __init__(self, path: str) -> None:
        self.path = path
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


if __name__ == "__main__":
    unittest.main()