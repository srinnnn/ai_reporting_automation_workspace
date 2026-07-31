from __future__ import annotations

from pathlib import Path

from backend.services.result_asset_service import ResultAssetService
from backend.services.report_service import MeituanReportRequest, MeituanWeeklyReportRequest, ReportService
from backend.workers.contracts import JsonObject, TaskRequest, TaskType
from backend.workers.executors.base import BaseTaskExecutor
from intranet_app.domain import ProcessingResult


class ReportExecutor(BaseTaskExecutor):
    def __init__(self, report_service: ReportService) -> None:
        if not isinstance(report_service, ReportService):
            raise TypeError("report_service must be ReportService")
        self._report_service = report_service

    def _execute(self, task_request: TaskRequest):
        if task_request.task_type != TaskType.REPORT_GENERATE:
            return self._failed(task_request.task_id, "task_type must be REPORT_GENERATE")
        try:
            result = self._build_report(task_request.payload)
            output = _processing_result_summary(result)
            asset = _save_result_asset(task_request.task_id, task_request.payload, result)
            if asset:
                output["result_asset"] = asset
                output["file_path"] = str(asset["file_path"])
                output["filename"] = str(asset["filename"])
            return self._success(task_request.task_id, output)
        except (TypeError, ValueError, RuntimeError, NotImplementedError, OSError) as exc:
            return self._failed(task_request.task_id, f"{type(exc).__name__}: {exc}")

    def _build_report(self, payload: JsonObject) -> ProcessingResult:
        report_period = _text(payload, "report_period")
        if report_period == "daily":
            return self._report_service.build_meituan_daily_report(
                MeituanReportRequest(
                    brand_id=_text(payload, "brand_id"),
                    platform=_text(payload, "platform"),
                    channel=_text(payload, "channel"),
                    report_date=_text(payload, "report_date"),
                )
            )
        if report_period == "weekly":
            return self._report_service.build_meituan_weekly_report(
                MeituanWeeklyReportRequest(
                    brand_id=_text(payload, "brand_id"),
                    platform=_text(payload, "platform"),
                    channel=_text(payload, "channel"),
                    start_date=_text(payload, "start_date"),
                    end_date=_text(payload, "end_date"),
                )
            )
        raise ValueError("report_period must be daily or weekly")


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


def _save_result_asset(task_id: int, payload: JsonObject, result: ProcessingResult) -> JsonObject:
    if not isinstance(task_id, int) or task_id <= 0:
        raise ValueError("task_id must be positive int")
    output_folder = _optional_text(payload, "output_folder")
    if not output_folder:
        return {}
    service = ResultAssetService(Path(output_folder))
    filename = _asset_filename(task_id, payload)
    asset = service.save_csv(filename, result.output_rows)
    asset_payload = asset.to_payload()
    assert asset_payload["filename"]
    return asset_payload


def _asset_filename(task_id: int, payload: JsonObject) -> str:
    report_period = _text(payload, "report_period")
    brand_id = _text(payload, "brand_id")
    platform = _text(payload, "platform")
    report_date = _optional_text(payload, "report_date") or _optional_text(payload, "date_window") or "unknown"
    filename = f"{task_id}_{brand_id}_{platform}_{report_period}_{report_date}_report.csv"
    assert filename.endswith(".csv")
    return filename


def _text(payload: JsonObject, field_name: str) -> str:
    value = payload.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must not be empty")
    result = value.strip()
    assert result
    return result


def _optional_text(payload: JsonObject, field_name: str) -> str:
    value = payload.get(field_name)
    if value is None:
        return ""
    if not isinstance(value, str):
        return ""
    result = value.strip()
    assert isinstance(result, str)
    return result
