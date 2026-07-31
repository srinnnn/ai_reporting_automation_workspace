from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Mapping

from backend.workers.contracts import TaskRequest, TaskResult, TaskType, WorkerTaskStatus
from backend.workers.executors import BaseTaskExecutor


@dataclass(frozen=True)
class TaskRunner:
    executors: Mapping[TaskType, BaseTaskExecutor]

    def __post_init__(self) -> None:
        if not isinstance(self.executors, Mapping):
            raise TypeError("executors must be Mapping")
        for task_type, executor in self.executors.items():
            if not isinstance(task_type, TaskType):
                raise TypeError("executor keys must be TaskType")
            if not isinstance(executor, BaseTaskExecutor):
                raise TypeError("executor values must be BaseTaskExecutor")

    def run(self, task_request: TaskRequest) -> TaskResult:
        if not isinstance(task_request, TaskRequest):
            raise TypeError("task_request must be TaskRequest")
        executor = self.executors.get(task_request.task_type)
        if executor is None:
            return _failed_result(task_request.task_id, f"unsupported task_type: {task_request.task_type}")
        try:
            result = executor.execute(task_request)
        except (TypeError, ValueError, RuntimeError, KeyError, AttributeError) as exc:
            logging.error("task executor failed: task=%s type=%s error=%s", task_request.task_id, task_request.task_type, type(exc).__name__)
            return _failed_result(task_request.task_id, f"{type(exc).__name__}: {exc}")
        assert isinstance(result, TaskResult)
        return result


def _failed_result(task_id: int, error: str) -> TaskResult:
    if not isinstance(task_id, int) or task_id <= 0:
        raise ValueError("task_id must be positive int")
    if not isinstance(error, str) or not error.strip():
        raise ValueError("error must not be empty")
    result = TaskResult(
        task_id=task_id,
        status=WorkerTaskStatus.FAILED,
        result={},
        error=error.strip(),
        finished_time=datetime.now(timezone.utc).isoformat(),
    )
    assert result.status == WorkerTaskStatus.FAILED
    return result
