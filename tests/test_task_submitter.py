from __future__ import annotations

import unittest

from backend.services.task_service import TaskCreateRequest, TaskResultSaveRequest, TaskService
from backend.workers.contracts import TaskRequest, TaskResult, TaskType, WorkerTaskStatus
from backend.workers.executors import BaseTaskExecutor
from backend.workers.task_runner import TaskRunner
from backend.workers.task_submitter import TaskSubmitter


class TaskSubmitterTests(unittest.TestCase):
    def test_creates_task_and_submits_to_runner(self) -> None:
        task_service = _TaskService()
        submitter = TaskSubmitter(task_service, TaskRunner({TaskType.REPORT_GENERATE: _SuccessExecutor()}))

        result = submitter.submit(TaskType.REPORT_GENERATE, _payload(), "admin")

        self.assertEqual(result.status, WorkerTaskStatus.SUCCESS)
        self.assertEqual(result.task_id, 101)
        self.assertEqual(task_service.created_request.task_type, "REPORT_GENERATE")
        self.assertEqual(task_service.saved_result.status.value, "success")

    def test_parameter_validation_rejects_missing_created_by(self) -> None:
        submitter = TaskSubmitter(_TaskService(), TaskRunner({TaskType.REPORT_GENERATE: _SuccessExecutor()}))

        with self.assertRaisesRegex(ValueError, "created_by"):
            submitter.submit(TaskType.REPORT_GENERATE, _payload(), "")

    def test_unknown_task_type_is_rejected_before_task_creation(self) -> None:
        task_service = _TaskService()
        submitter = TaskSubmitter(task_service, TaskRunner({TaskType.REPORT_GENERATE: _SuccessExecutor()}))

        with self.assertRaisesRegex(ValueError, "unsupported task_type"):
            submitter.submit("UNKNOWN", _payload(), "admin")

        self.assertIsNone(task_service.created_request)

    def test_returns_task_id_in_task_result(self) -> None:
        submitter = TaskSubmitter(_TaskService(), TaskRunner({TaskType.AI_CONTENT_GENERATE: _SuccessExecutor()}))

        result = submitter.submit("AI_CONTENT_GENERATE", _payload(), "admin")

        self.assertEqual(result.task_id, 101)


class _TaskService(TaskService):
    def __init__(self) -> None:
        self.created_request: TaskCreateRequest | None = None
        self.saved_result: TaskResultSaveRequest | None = None

    def create_task(self, request: TaskCreateRequest) -> int:
        self.created_request = request
        return 101

    def save_task_result(self, request: TaskResultSaveRequest) -> int:
        self.saved_result = request
        return 202


class _SuccessExecutor(BaseTaskExecutor):
    def _execute(self, task_request: TaskRequest) -> TaskResult:
        return TaskResult(
            task_id=task_request.task_id,
            status=WorkerTaskStatus.SUCCESS,
            result={"submitted": True, "task_type": task_request.task_type.value},
            error="",
            finished_time="2026-07-30T17:35:00+08:00",
        )


def _payload() -> dict[str, object]:
    return {
        "task_name": "Anta report submission",
        "business_unit": "anta_retail_team",
        "brand_id": "anta_kids",
        "brand_name": "Anta Kids",
        "platform": "meituan",
        "channel": "instant_retail",
        "report_period": "daily",
        "report_date": "20260725",
        "output_folder": "runtime/results",
    }


if __name__ == "__main__":
    unittest.main()
