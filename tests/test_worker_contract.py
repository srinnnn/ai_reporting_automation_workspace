from __future__ import annotations

import unittest

from backend.workers.contracts import TaskRequest, TaskResult, TaskType, WorkerTaskStatus
from backend.workers.executors import BaseTaskExecutor


class WorkerContractTests(unittest.TestCase):
    def test_task_request_creation(self) -> None:
        request = TaskRequest(
            task_id=1,
            task_type=TaskType.DATA_IMPORT,
            created_by="admin",
            payload={"brand_id": "anta_kids", "dates": ["20260725"]},
            created_time="2026-07-30T16:50:00+08:00",
        )

        self.assertEqual(request.task_id, 1)
        self.assertEqual(request.task_type, TaskType.DATA_IMPORT)
        self.assertEqual(request.payload["brand_id"], "anta_kids")

    def test_task_request_rejects_non_json_payload(self) -> None:
        with self.assertRaisesRegex(TypeError, "JSON-compatible"):
            TaskRequest(
                task_id=1,
                task_type=TaskType.REPORT_GENERATE,
                created_by="admin",
                payload={"path": object()},
                created_time="2026-07-30T16:50:00+08:00",
            )

    def test_task_result_creation(self) -> None:
        result = TaskResult(
            task_id=1,
            status=WorkerTaskStatus.SUCCESS,
            result={"output_file": "runtime/results/report.csv", "row_count": 10},
            error="",
            finished_time="2026-07-30T16:51:00+08:00",
        )

        self.assertEqual(result.status, WorkerTaskStatus.SUCCESS)
        self.assertEqual(result.result["row_count"], 10)

    def test_failed_task_result_requires_error(self) -> None:
        with self.assertRaisesRegex(ValueError, "error"):
            TaskResult(
                task_id=1,
                status=WorkerTaskStatus.FAILED,
                result={},
                error="",
                finished_time="2026-07-30T16:51:00+08:00",
            )

    def test_executor_interface_call(self) -> None:
        executor = _EchoExecutor()
        request = TaskRequest(
            task_id=7,
            task_type=TaskType.AI_CONTENT_GENERATE,
            created_by="admin",
            payload={"task": "p2_copy"},
            created_time="2026-07-30T16:50:00+08:00",
        )

        result = executor.execute(request)

        self.assertEqual(result.task_id, 7)
        self.assertEqual(result.status, WorkerTaskStatus.SUCCESS)
        self.assertEqual(result.result["task_type"], "AI_CONTENT_GENERATE")


class _EchoExecutor(BaseTaskExecutor):
    def _execute(self, task_request: TaskRequest) -> TaskResult:
        return TaskResult(
            task_id=task_request.task_id,
            status=WorkerTaskStatus.SUCCESS,
            result={"task_type": task_request.task_type.value},
            error="",
            finished_time="2026-07-30T16:51:00+08:00",
        )


if __name__ == "__main__":
    unittest.main()
