from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from backend.services.assets.asset_service import ResultAssetService
from backend.services.assets.providers.local_provider import LocalStorageProvider
from backend.services.report_service import ReportService
from backend.services.task_query_service import TaskQueryService, TaskReadModel
from backend.services.task_result_service import TaskResultService
from backend.services.task_service import TaskCreateRequest, TaskResultSaveRequest, TaskService
from backend.workers.contracts import TaskRequest, TaskResult, TaskType, WorkerTaskStatus
from backend.workers.executors import BaseTaskExecutor
from backend.workers.executors.report_executor import ReportExecutor
from backend.workers.task_runner import TaskRunner
from backend.workers.task_submitter import TaskSubmitter
from intranet_app.domain import ProcessingResult


class TaskSubmitterFailureStabilityTests(unittest.TestCase):
    def test_executor_exception_is_saved_as_failed_task_result(self) -> None:
        task_service = _RecordingTaskService()
        submitter = TaskSubmitter(task_service, TaskRunner({TaskType.REPORT_GENERATE: _RaisingExecutor()}))

        result = submitter.submit(TaskType.REPORT_GENERATE, _payload(), "admin")

        self.assertEqual(result.status, WorkerTaskStatus.FAILED)
        self.assertIn("RuntimeError", result.error)
        self.assertIsNotNone(task_service.created_request)
        self.assertIsNotNone(task_service.saved_result)
        self.assertEqual(task_service.saved_result.status.value, "failed")
        self.assertIn("executor failed", task_service.saved_result.error_message)

    def test_failed_task_status_is_persisted_when_executor_returns_failed_result(self) -> None:
        task_service = _RecordingTaskService()
        submitter = TaskSubmitter(task_service, TaskRunner({TaskType.REPORT_GENERATE: _FailedExecutor()}))

        result = submitter.submit(TaskType.REPORT_GENERATE, _payload(), "admin")

        self.assertEqual(result.status, WorkerTaskStatus.FAILED)
        self.assertEqual(result.error, "foundation data missing")
        self.assertIsNotNone(task_service.saved_result)
        self.assertEqual(task_service.saved_result.status.value, "failed")
        self.assertEqual(task_service.saved_result.result_message, "")
        self.assertEqual(task_service.saved_result.error_message, "foundation data missing")

    def test_result_save_failure_is_not_silently_swallowed(self) -> None:
        task_service = _FailingSaveTaskService()
        submitter = TaskSubmitter(task_service, TaskRunner({TaskType.REPORT_GENERATE: _SuccessExecutor()}))

        with self.assertRaisesRegex(RuntimeError, "result persistence failed"):
            submitter.submit(TaskType.REPORT_GENERATE, _payload(), "admin")

        self.assertIsNotNone(task_service.created_request)


class ResultAssetConsistencyTests(unittest.TestCase):
    def test_success_task_must_have_existing_asset_to_be_downloadable(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            asset = _write_asset(root, "daily.csv")
            service = TaskResultService(_StaticTaskQueryService(_read_model("success", _asset_payload(asset))), root)

            view = service.get_result(1)
            download = service.get_download_info(1)

            self.assertEqual(view.filename, "daily.csv")
            self.assertEqual(view.file_path, "task-results/1/daily.csv")
            self.assertEqual(download.path, asset.resolve())

    def test_success_task_with_missing_asset_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            missing = root / "missing.csv"
            service = TaskResultService(_StaticTaskQueryService(_read_model("success", _asset_payload(missing))), root)

            with self.assertRaises(FileNotFoundError):
                service.get_result(1)

    def test_failed_task_cannot_expose_asset_even_if_payload_contains_one(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            asset = _write_asset(root, "failed.csv")
            service = TaskResultService(_StaticTaskQueryService(_read_model("failed", _asset_payload(asset))), root)

            with self.assertRaisesRegex(ValueError, "not downloadable"):
                service.get_result(1)
            with self.assertRaisesRegex(ValueError, "successful"):
                service.get_download_info(1)


class DailyReportTaskE2ETests(unittest.TestCase):
    def test_daily_report_task_generates_asset_and_download_info(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            result_dir = root / "results"
            task_service = _RecordingTaskService()
            report_executor = ReportExecutor(
                _DailyReportService(_daily_input_rows()),
                ResultAssetService(LocalStorageProvider(result_dir)),
            )
            submitter = TaskSubmitter(task_service, TaskRunner({TaskType.REPORT_GENERATE: report_executor}))

            result = submitter.submit(TaskType.REPORT_GENERATE, _payload(output_folder=str(result_dir)), "admin")

            self.assertEqual(result.status, WorkerTaskStatus.SUCCESS)
            self.assertIn("result_asset", result.result)
            asset_payload = result.result["result_asset"]
            self.assertIsInstance(asset_payload, dict)
            asset_path = Path(str(asset_payload["file_path"]))
            self.assertTrue(asset_path.exists())
            self.assertEqual(asset_payload["filename"], "101_anta_kids_meituan_daily_20260725_report.csv")
            self.assertIsNotNone(task_service.saved_result)
            download_service = TaskResultService(
                _StaticTaskQueryService(_read_model("success", asset_payload, result=result.result)),
                result_dir,
            )

            download = download_service.get_download_info(101)

            self.assertEqual(download.filename, "101_anta_kids_meituan_daily_20260725_report.csv")
            self.assertEqual(download.path, asset_path.resolve())
            with download.path.open("r", encoding="utf-8-sig", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(rows, [{"metric": "sales", "value": "100"}])


class _RecordingTaskService(TaskService):
    def __init__(self) -> None:
        self.created_request: TaskCreateRequest | None = None
        self.saved_result: TaskResultSaveRequest | None = None

    def create_task(self, request: TaskCreateRequest) -> int:
        self.created_request = request
        return 101

    def save_task_result(self, request: TaskResultSaveRequest) -> int:
        self.saved_result = request
        return 202


class _FailingSaveTaskService(_RecordingTaskService):
    def save_task_result(self, request: TaskResultSaveRequest) -> int:
        self.saved_result = request
        raise RuntimeError("result persistence failed")


class _RaisingExecutor(BaseTaskExecutor):
    def _execute(self, task_request: TaskRequest) -> TaskResult:
        raise RuntimeError("executor failed")


class _FailedExecutor(BaseTaskExecutor):
    def _execute(self, task_request: TaskRequest) -> TaskResult:
        return TaskResult(
            task_id=task_request.task_id,
            status=WorkerTaskStatus.FAILED,
            result={},
            error="foundation data missing",
            finished_time="2026-08-03T10:00:00+08:00",
        )


class _SuccessExecutor(BaseTaskExecutor):
    def _execute(self, task_request: TaskRequest) -> TaskResult:
        return TaskResult(
            task_id=task_request.task_id,
            status=WorkerTaskStatus.SUCCESS,
            result={"ok": True},
            error="",
            finished_time="2026-08-03T10:00:00+08:00",
        )


class _DailyReportService(ReportService):
    def __init__(self, input_rows: list[dict[str, str]]) -> None:
        self.input_rows = input_rows
        self.last_report_date = ""

    def build_meituan_daily_report(self, request):
        self.last_report_date = request.report_date
        if not self.input_rows:
            raise ValueError("daily input rows missing")
        return ProcessingResult(
            module="anta_meituan_daily",
            output_rows=[{"metric": "sales", "value": self.input_rows[0]["sales"]}],
            summary={"report_date": request.report_date, "source_rows": str(len(self.input_rows))},
            warnings=[],
        )


def _payload(output_folder: str = "runtime/results") -> dict[str, object]:
    return {
        "task_name": "Anta daily report",
        "business_unit": "anta_retail_team",
        "brand_id": "anta_kids",
        "brand_name": "Anta Kids",
        "platform": "meituan",
        "channel": "instant_retail",
        "report_period": "daily",
        "report_date": "20260725",
        "date_window": "20260725",
        "output_folder": output_folder,
    }


def _daily_input_rows() -> list[dict[str, str]]:
    return [{"date": "20260725", "sales": "100"}]


def _write_asset(root: Path, filename: str) -> Path:
    path = root / filename
    path.write_text("metric,value\nsales,100\n", encoding="utf-8")
    return path


def _asset_payload(path: Path) -> dict[str, object]:
    return {"file_path": str(path), "filename": path.name, "size": path.stat().st_size if path.exists() else 0}


class _StaticTaskQueryService(TaskQueryService):
    def __init__(self, task: TaskReadModel) -> None:
        self._task = task

    def get_task(self, task_id: int) -> TaskReadModel | None:
        if task_id == self._task.task_id:
            return self._task
        return None


def _read_model(status: str, result_asset: dict[str, object] | None, result: dict[str, object] | None = None) -> TaskReadModel:
    return TaskReadModel(
        task_id=101 if result else 1,
        task_type="REPORT_GENERATE",
        status=status,
        created_by="admin",
        created_time="2026-08-03T10:00:00+08:00",
        result=result or ({"result_asset": result_asset} if result_asset else {}),
        error="" if status == "success" else "foundation data missing",
        owner="admin",
        brand_id="anta_kids",
        business_unit="anta_retail_team",
        platform="meituan",
        channel="instant_retail",
        updated_at="2026-08-03T10:01:00+08:00",
        scope_snapshot={"brand_id": "anta_kids"},
        result_asset=result_asset,
    )


if __name__ == "__main__":
    unittest.main()