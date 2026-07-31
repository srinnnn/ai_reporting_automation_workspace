from __future__ import annotations

from pathlib import Path

from backend.services.data_foundation_service import DataFoundationProcessRequest, DataFoundationService
from backend.workers.contracts import JsonObject, TaskRequest, TaskType
from backend.workers.executors.base import BaseTaskExecutor
from intranet_app.data_foundation import UploadMetadata


class DataImportExecutor(BaseTaskExecutor):
    def __init__(self, data_foundation_service: DataFoundationService) -> None:
        if not isinstance(data_foundation_service, DataFoundationService):
            raise TypeError("data_foundation_service must be DataFoundationService")
        self._data_foundation_service = data_foundation_service

    def _execute(self, task_request: TaskRequest):
        if task_request.task_type != TaskType.DATA_IMPORT:
            return self._failed(task_request.task_id, "task_type must be DATA_IMPORT")
        try:
            request = _build_process_request(task_request.payload)
            result = self._data_foundation_service.process_rows(request)
            return self._success(
                task_request.task_id,
                {
                    "import_batch_id": result.import_batch_id,
                    "status": result.status,
                    "imported": result.imported,
                    "row_count": len(result.plan.normalized_rows),
                    "recognized_file_type": result.plan.recognition.file_type,
                },
            )
        except (TypeError, ValueError, RuntimeError) as exc:
            return self._failed(task_request.task_id, f"{type(exc).__name__}: {exc}")


def _build_process_request(payload: JsonObject) -> DataFoundationProcessRequest:
    if not isinstance(payload, dict):
        raise TypeError("payload must be dict")
    metadata_payload = _dict(payload, "metadata")
    rows = _rows(payload, "rows")
    result = DataFoundationProcessRequest(
        import_batch_id=_text(payload, "import_batch_id"),
        metadata=UploadMetadata(
            business_unit=_text(metadata_payload, "business_unit"),
            brand_id=_text(metadata_payload, "brand_id"),
            brand_name=_text(metadata_payload, "brand_name"),
            platform=_text(metadata_payload, "platform"),
            channel=_text(metadata_payload, "channel"),
            project_code=_text(metadata_payload, "project_code"),
            declared_file_type=_text(metadata_payload, "declared_file_type"),
            data_start_date=_text(metadata_payload, "data_start_date"),
            data_end_date=_text(metadata_payload, "data_end_date"),
            uploaded_by=_text(metadata_payload, "uploaded_by"),
        ),
        rows=rows,
        known_store_ids=_tuple_text(payload, "known_store_ids"),
        known_product_codes=_tuple_text(payload, "known_product_codes"),
        original_file_name=_text(payload, "original_file_name"),
        stored_file_path=Path(_text(payload, "stored_file_path")),
        file_sha256=_text(payload, "file_sha256"),
    )
    assert isinstance(result, DataFoundationProcessRequest)
    return result


def _dict(payload: JsonObject, field_name: str) -> JsonObject:
    value = payload.get(field_name)
    if not isinstance(value, dict):
        raise ValueError(f"{field_name} must be dict")
    return value


def _rows(payload: JsonObject, field_name: str) -> list[dict[str, str]]:
    value = payload.get(field_name)
    if not isinstance(value, list):
        raise ValueError(f"{field_name} must be list")
    rows: list[dict[str, str]] = []
    for row in value:
        if not isinstance(row, dict):
            raise ValueError(f"{field_name} rows must be dict")
        rows.append({str(key): str(item) for key, item in row.items()})
    assert isinstance(rows, list)
    return rows


def _tuple_text(payload: JsonObject, field_name: str) -> tuple[str, ...]:
    value = payload.get(field_name)
    if not isinstance(value, list):
        raise ValueError(f"{field_name} must be list")
    result = tuple(str(item).strip() for item in value if str(item).strip())
    assert isinstance(result, tuple)
    return result


def _text(payload: JsonObject, field_name: str) -> str:
    value = payload.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must not be empty")
    result = value.strip()
    assert result
    return result
