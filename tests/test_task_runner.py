from __future__ import annotations

import unittest

from backend.workers.contracts import TaskRequest, TaskResult, TaskType, WorkerTaskStatus
from backend.workers.executors import BaseTaskExecutor
from backend.workers.task_runner import TaskRunner


class TaskRunnerTests(unittest.TestCase):
    def test_selects_correct_executor(self) -> None:
        data_import_executor = _RecordingExecutor("data")
        report_executor = _RecordingExecutor("report")
        ai_executor = _RecordingExecutor("ai")
        runner = TaskRunner(
            {
                TaskType.DATA_IMPORT: data_import_executor,
                TaskType.REPORT_GENERATE: report_executor,
                TaskType.AI_CONTENT_GENERATE: ai_executor,
            }
        )

        result = runner.run(_task_request(1, TaskType.REPORT_GENERATE))

        self.assertEqual(result.status, WorkerTaskStatus.SUCCESS)
        self.assertEqual(result.result["executor"], "report")
        self.assertEqual(data_import_executor.call_count, 0)
        self.assertEqual(report_executor.call_count, 1)
        self.assertEqual(ai_executor.call_count, 0)

    def test_runs_executor_normally(self) -> None:
        runner = TaskRunner({TaskType.AI_CONTENT_GENERATE: _RecordingExecutor("ai")})

        result = runner.run(_task_request(2, TaskType.AI_CONTENT_GENERATE))

        self.assertEqual(result.task_id, 2)
        self.assertEqual(result.status, WorkerTaskStatus.SUCCESS)
        self.assertEqual(result.result["task_type"], "AI_CONTENT_GENERATE")

    def test_unknown_task_type_returns_failed(self) -> None:
        request = _task_request(3, TaskType.DATA_IMPORT)
        object.__setattr__(request, "task_type", "UNKNOWN")
        runner = TaskRunner({TaskType.DATA_IMPORT: _RecordingExecutor("data")})

        result = runner.run(request)

        self.assertEqual(result.status, WorkerTaskStatus.FAILED)
        self.assertIn("unsupported task_type", result.error)

    def test_executor_exception_returns_failed(self) -> None:
        runner = TaskRunner({TaskType.REPORT_GENERATE: _FailingExecutor()})

        result = runner.run(_task_request(4, TaskType.REPORT_GENERATE))

        self.assertEqual(result.status, WorkerTaskStatus.FAILED)
        self.assertIn("executor failed", result.error)


class _RecordingExecutor(BaseTaskExecutor):
    def __init__(self, name: str) -> None:
        self.name = name
        self.call_count = 0

    def _execute(self, task_request: TaskRequest) -> TaskResult:
        self.call_count += 1
        return TaskResult(
            task_id=task_request.task_id,
            status=WorkerTaskStatus.SUCCESS,
            result={"executor": self.name, "task_type": task_request.task_type.value},
            error="",
            finished_time="2026-07-30T17:20:00+08:00",
        )


class _FailingExecutor(BaseTaskExecutor):
    def _execute(self, task_request: TaskRequest) -> TaskResult:
        raise RuntimeError("executor failed")


def _task_request(task_id: int, task_type: TaskType) -> TaskRequest:
    return TaskRequest(
        task_id=task_id,
        task_type=task_type,
        created_by="admin",
        payload={"brand_id": "anta_kids"},
        created_time="2026-07-30T17:20:00+08:00",
    )


if __name__ == "__main__":
    unittest.main()
