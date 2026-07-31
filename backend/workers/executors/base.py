from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone

from backend.workers.contracts import JsonObject, TaskRequest, TaskResult, WorkerTaskStatus


class BaseTaskExecutor(ABC):
    def execute(self, task_request: TaskRequest) -> TaskResult:
        if not isinstance(task_request, TaskRequest):
            raise TypeError("task_request must be TaskRequest")
        result = self._execute(task_request)
        if not isinstance(result, TaskResult):
            raise TypeError("executor result must be TaskResult")
        assert isinstance(result, TaskResult)
        return result

    @abstractmethod
    def _execute(self, task_request: TaskRequest) -> TaskResult:
        if not isinstance(task_request, TaskRequest):
            raise TypeError("task_request must be TaskRequest")
        raise NotImplementedError

    def _success(self, task_id: int, result: JsonObject) -> TaskResult:
        if not isinstance(task_id, int) or task_id <= 0:
            raise ValueError("task_id must be positive int")
        if not isinstance(result, dict):
            raise TypeError("result must be dict")
        task_result = TaskResult(
            task_id=task_id,
            status=WorkerTaskStatus.SUCCESS,
            result=result,
            error="",
            finished_time=_utc_now(),
        )
        assert task_result.status == WorkerTaskStatus.SUCCESS
        return task_result

    def _failed(self, task_id: int, error: str) -> TaskResult:
        if not isinstance(task_id, int) or task_id <= 0:
            raise ValueError("task_id must be positive int")
        if not isinstance(error, str) or not error.strip():
            raise ValueError("error must not be empty")
        task_result = TaskResult(
            task_id=task_id,
            status=WorkerTaskStatus.FAILED,
            result={},
            error=error.strip(),
            finished_time=_utc_now(),
        )
        assert task_result.status == WorkerTaskStatus.FAILED
        return task_result


def _utc_now() -> str:
    result = datetime.now(timezone.utc).isoformat()
    assert result
    return result
