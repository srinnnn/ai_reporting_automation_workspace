from __future__ import annotations

from backend.services.ai_content_service import AIContentService
from backend.workers.contracts import JsonObject, TaskRequest, TaskType
from backend.workers.executors.base import BaseTaskExecutor
from intranet_app.content_pipeline import P2ContentRequest
from intranet_app.domain import ProcessingResult


class AIContentExecutor(BaseTaskExecutor):
    def __init__(self, ai_content_service: AIContentService) -> None:
        if not isinstance(ai_content_service, AIContentService):
            raise TypeError("ai_content_service must be AIContentService")
        self._ai_content_service = ai_content_service

    def _execute(self, task_request: TaskRequest):
        if task_request.task_type != TaskType.AI_CONTENT_GENERATE:
            return self._failed(task_request.task_id, "task_type must be AI_CONTENT_GENERATE")
        try:
            result = self._ai_content_service.build_content_pack(_build_p2_request(task_request.payload))
            return self._success(task_request.task_id, _processing_result_summary(result))
        except (TypeError, ValueError, RuntimeError) as exc:
            return self._failed(task_request.task_id, f"{type(exc).__name__}: {exc}")


def _build_p2_request(payload: JsonObject) -> P2ContentRequest:
    forbidden_words = payload.get("forbidden_words")
    if not isinstance(forbidden_words, list):
        raise ValueError("forbidden_words must be list")
    result = P2ContentRequest(
        brand_id=_text(payload, "brand_id"),
        brand_name=_text(payload, "brand_name"),
        platform=_text(payload, "platform"),
        channel=_text(payload, "channel"),
        start_date=_text(payload, "start_date"),
        end_date=_text(payload, "end_date"),
        task_type=_text(payload, "task_type"),
        output_count=_int(payload, "output_count"),
        brand_profile=_text(payload, "brand_profile"),
        forbidden_words=tuple(str(item) for item in forbidden_words),
    )
    assert isinstance(result, P2ContentRequest)
    return result


def _processing_result_summary(result: ProcessingResult) -> JsonObject:
    if not isinstance(result, ProcessingResult):
        raise TypeError("result must be ProcessingResult")
    summary = {str(key): str(value) for key, value in result.summary.items()}
    output = {
        "module": result.module,
        "output_row_count": len(result.output_rows),
        "warning_count": len(result.warnings),
        "summary": summary,
    }
    assert isinstance(output, dict)
    return output


def _int(payload: JsonObject, field_name: str) -> int:
    value = payload.get(field_name)
    if not isinstance(value, int) or value <= 0:
        raise ValueError(f"{field_name} must be positive int")
    return value


def _text(payload: JsonObject, field_name: str) -> str:
    value = payload.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must not be empty")
    result = value.strip()
    assert result
    return result
