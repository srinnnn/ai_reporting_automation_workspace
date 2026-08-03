from __future__ import annotations

import unittest

from backend.services.task_query_service import TaskReadModel
from backend.services.task_result_service import TaskResultView
from intranet_app.app import IntranetApp
from intranet_app.auth import PasswordHash
from intranet_app.storage import UserRecord


class TaskDetailDiagnosticsTests(unittest.TestCase):
    def test_report_task_detail_shows_static_execution_flow(self) -> None:
        app = object.__new__(IntranetApp)
        app._task_query_service = lambda: _TaskQueryService()
        app._task_result_service = lambda: _TaskResultService()

        page = app._task_detail_page(_user(), "/tasks/1")

        self.assertIn("Execution Flow", page)
        self.assertIn("TaskSubmitter", page)
        self.assertIn("TaskRunner", page)
        self.assertIn("ReportExecutor", page)
        self.assertIn("ReportService", page)
        self.assertIn("ResultAsset", page)

    def test_success_task_detail_shows_result_asset_status(self) -> None:
        app = object.__new__(IntranetApp)
        app._task_query_service = lambda: _TaskQueryService()
        app._task_result_service = lambda: _TaskResultService()

        page = app._task_detail_page(_user(), "/tasks/1")

        self.assertIn("Result Asset", page)
        self.assertIn("download available", page)
        self.assertIn("true", page)
        self.assertIn("daily.csv", page)
        self.assertIn("task-results/1/daily.csv", page)
        self.assertIn("size", page)

    def test_failed_task_detail_shows_error_diagnostics(self) -> None:
        app = object.__new__(IntranetApp)
        app._task_query_service = lambda: _TaskQueryService()
        app._task_result_service = lambda: _TaskResultService()

        page = app._task_detail_page(_user(), "/tasks/2")

        self.assertIn("Error Diagnostics", page)
        self.assertIn("failed", page)
        self.assertIn("foundation data missing", page)
        self.assertIn("2026-07-31T09:55:00+08:00", page)
        self.assertIn("2026-07-31T10:01:00+08:00", page)
        self.assertIn("download available", page)
        self.assertIn("false", page)

    def test_ai_task_detail_flow_uses_ai_executor_and_service(self) -> None:
        app = object.__new__(IntranetApp)
        app._task_query_service = lambda: _TaskQueryService()
        app._task_result_service = lambda: _TaskResultService()

        page = app._task_detail_page(_user(), "/tasks/3")

        self.assertIn("AIContentExecutor", page)
        self.assertIn("AIContentService", page)


def _user() -> UserRecord:
    return UserRecord(
        id=1,
        username="admin",
        display_name="Admin",
        role="admin",
        password_hash=PasswordHash("salt", "digest"),
    )


class _TaskQueryService:
    def get_task(self, task_id: int):
        if task_id == 1:
            return _task(
                1,
                "REPORT_GENERATE",
                "success",
                {"output_row_count": 3, "result_asset": {"filename": "daily.csv"}},
                "",
                "2026-07-31T10:00:00+08:00",
            )
        if task_id == 2:
            return _task(2, "REPORT_GENERATE", "failed", {}, "foundation data missing", "2026-07-31T10:01:00+08:00")
        if task_id == 3:
            return _task(3, "AI_CONTENT_GENERATE", "pending", {}, "", "2026-07-31T10:02:00+08:00")
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


def _task(task_id: int, task_type: str, status: str, result: dict[str, object], error: str, updated_at: str) -> TaskReadModel:
    return TaskReadModel(
        task_id=task_id,
        task_type=task_type,
        status=status,
        created_by="admin",
        created_time="2026-07-31T09:55:00+08:00",
        updated_at=updated_at,
        result=result,
        error=error,
    )


if __name__ == "__main__":
    unittest.main()
