from __future__ import annotations

import unittest
from types import SimpleNamespace

from backend.services.task_query_service import TaskReadModel
from backend.services.task_result_service import TaskResultView
from intranet_app.app import IntranetApp
from intranet_app.auth import PasswordHash
from intranet_app.storage import UserRecord


class TaskPageTests(unittest.TestCase):
    def test_tasks_page_access(self) -> None:
        app = object.__new__(IntranetApp)
        app._context = lambda handler: SimpleNamespace(user=_user(), token="token")
        app._task_query_service = lambda: _TaskQueryService()
        sent: dict[str, object] = {}
        app._send_html = lambda handler, content, status=200: sent.update({"content": content, "status": status})
        handler = SimpleNamespace(path="/tasks")

        app.handle_get(handler)

        self.assertEqual(sent["status"], 200)
        self.assertIn("任务状态", str(sent["content"]))
        self.assertIn("/tasks/1", str(sent["content"]))
        self.assertIn("REPORT_GENERATE", str(sent["content"]))

    def test_task_detail_page_shows_status_and_error(self) -> None:
        app = object.__new__(IntranetApp)
        app._task_query_service = lambda: _TaskQueryService()
        app._task_result_service = lambda: _TaskResultService()

        page = app._task_detail_page(_user(), "/tasks/2")

        self.assertIn("任务详情 #2", page)
        self.assertIn("failed", page)
        self.assertIn("foundation data missing", page)
        self.assertIn("暂无可下载文件", page)

    def test_task_detail_page_has_download_link_for_result_asset(self) -> None:
        app = object.__new__(IntranetApp)
        app._task_query_service = lambda: _TaskQueryService()
        app._task_result_service = lambda: _TaskResultService()

        page = app._task_detail_page(_user(), "/tasks/1")

        self.assertIn("/api/tasks/1/download", page)
        self.assertIn("daily.csv", page)
        self.assertIn("output_row_count", page)


class _TaskQueryService:
    def list_tasks(self):
        return [_task(1, "success", {"output_row_count": 3}), _task(2, "failed", {})]

    def get_task(self, task_id: int):
        if task_id == 1:
            return _task(1, "success", {"output_row_count": 3, "result_asset": {"filename": "daily.csv"}})
        if task_id == 2:
            return _task(2, "failed", {}, "foundation data missing")
        return None


class _TaskResultService:
    def get_result(self, task_id: int) -> TaskResultView:
        if task_id != 1:
            raise ValueError("not downloadable")
        return TaskResultView(
            task_id=1,
            status="success",
            result_asset={"filename": "daily.csv", "size": 20},
            filename="daily.csv",
            file_path="task-results/1/daily.csv",
        )


def _task(task_id: int, status: str, result: dict[str, object], error: str = "") -> TaskReadModel:
    return TaskReadModel(
        task_id=task_id,
        task_type="REPORT_GENERATE",
        status=status,
        created_by="admin",
        created_time="2026-07-31T09:55:00+08:00",
        result=result,
        error=error,
    )


def _user() -> UserRecord:
    return UserRecord(
        id=1,
        username="admin",
        display_name="Admin",
        role="admin",
        password_hash=PasswordHash("salt", "digest"),
    )


if __name__ == "__main__":
    unittest.main()
