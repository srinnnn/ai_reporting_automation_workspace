from __future__ import annotations

import json
import unittest

from backend.repositories.interfaces import AutomationTaskCreate, TaskRepository, TaskRunCreate
from backend.services.task_query_service import TaskQueryFilters, TaskQueryService
from intranet_app.storage import AutomationRunRecord, AutomationTaskRecord


class TaskQueryServiceTests(unittest.TestCase):
    def test_get_task_returns_read_model(self) -> None:
        service = TaskQueryService(_TaskRepository())

        task = service.get_task(1)

        self.assertIsNotNone(task)
        self.assertEqual(task.task_id, 1)
        self.assertEqual(task.task_type, "REPORT_GENERATE")
        self.assertEqual(task.status, "success")
        self.assertEqual(task.created_by, "admin")
        self.assertEqual(task.result["output_row_count"], 3)
        self.assertEqual(task.error, "")
        self.assertEqual(task.owner, "admin")
        self.assertEqual(task.brand_id, "anta_kids")
        self.assertEqual(task.business_unit, "anta_retail_team")
        self.assertEqual(task.platform, "meituan")
        self.assertEqual(task.channel, "instant_retail")
        self.assertEqual(task.updated_at, "2026-07-30T17:45:00+08:00")
        self.assertEqual(task.scope_snapshot["brand_id"], "anta_kids")
        self.assertEqual(task.scope_snapshot["business_unit"], "anta_retail_team")
        self.assertEqual(task.result_asset["filename"], "daily.csv")

    def test_list_tasks_supports_filters(self) -> None:
        service = TaskQueryService(_TaskRepository())

        tasks = service.list_tasks(TaskQueryFilters(task_type="AI_CONTENT_GENERATE", created_by="copywriter"))

        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0].task_id, 3)
        self.assertEqual(tasks[0].status, "pending")

    def test_list_failed_tasks_returns_failed_rows(self) -> None:
        service = TaskQueryService(_TaskRepository())

        failed_tasks = service.list_failed_tasks()

        self.assertEqual(len(failed_tasks), 1)
        self.assertEqual(failed_tasks[0].task_id, 2)
        self.assertEqual(failed_tasks[0].error, "foundation data missing")

    def test_get_task_summary_counts_statuses(self) -> None:
        service = TaskQueryService(_TaskRepository())

        summary = service.get_task_summary()

        self.assertEqual(summary.total, 4)
        self.assertEqual(summary.success_count, 1)
        self.assertEqual(summary.failed_count, 1)
        self.assertEqual(summary.running_count, 1)
        self.assertEqual(summary.pending_count, 1)

    def test_read_model_remains_compatible_with_old_minimal_constructor(self) -> None:
        task = TaskQueryService(_TaskRepository()).get_task(3)

        self.assertIsNotNone(task)
        self.assertIsNone(task.result_asset)
        self.assertEqual(task.result, {})


class _TaskRepository(TaskRepository):
    def create_task(self, request: AutomationTaskCreate) -> int:
        raise NotImplementedError

    def update_task_status(self, task_id: int, status: str) -> None:
        raise NotImplementedError

    def get_task(self, task_id: int) -> AutomationTaskRecord | None:
        for task in self.list_tasks():
            if task.id == task_id:
                return task
        return None

    def save_task_result(self, request: TaskRunCreate) -> int:
        raise NotImplementedError

    def list_tasks(self) -> list[AutomationTaskRecord]:
        return [
            _task(1, "REPORT_GENERATE", "admin", True),
            _task(2, "DATA_IMPORT", "admin", True),
            _task(3, "AI_CONTENT_GENERATE", "copywriter", True),
            _task(4, "REPORT_GENERATE", "admin", True),
        ]

    def list_task_runs(self, limit: int = 200) -> list[AutomationRunRecord]:
        return [
            _run(11, 4, "running", "started", "admin"),
            _run(10, 2, "failed", "error: foundation data missing", "admin"),
            _run(
                9,
                1,
                "success",
                json.dumps(
                    {
                        "output_row_count": 3,
                        "result_asset": {
                            "filename": "daily.csv",
                            "file_path": "runtime/results/daily.csv",
                            "size": 20,
                        },
                    },
                    ensure_ascii=False,
                ),
                "admin",
            ),
        ]


def _task(task_id: int, task_type: str, owner: str, enabled: bool) -> AutomationTaskRecord:
    return AutomationTaskRecord(
        id=task_id,
        task_name=f"task-{task_id}",
        business_unit="anta_retail_team",
        brand_id="anta_kids",
        brand_name="Anta Kids",
        platform="meituan",
        channel="instant_retail",
        file_type=task_type,
        frequency="daily",
        scheduled_time="09:30",
        date_window="20260725",
        enabled=enabled,
        output_folder="runtime/results",
        owner=owner,
        notes="",
        created_at="2026-07-30T17:45:00+08:00",
        updated_at="2026-07-30T17:45:00+08:00",
    )


def _run(run_id: int, task_id: int, status: str, message: str, executed_by: str) -> AutomationRunRecord:
    return AutomationRunRecord(
        id=run_id,
        task_id=task_id,
        task_name=f"task-{task_id}",
        run_date="20260725",
        status=status,
        downloaded_file_count=0,
        synced_file_count=0,
        message=message,
        executed_by=executed_by,
        created_at="2026-07-30T17:46:00+08:00",
    )


if __name__ == "__main__":
    unittest.main()
