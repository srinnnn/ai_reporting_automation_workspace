from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from backend.adapters.report_task_adapter import build_daily_report_task_payload
from backend.repositories.interfaces import AutomationTaskCreate, FoundationRepository, TaskRepository, TaskRunCreate
from backend.services.assets.asset_service import ResultAssetService
from backend.services.assets.providers.local_provider import LocalStorageProvider
from backend.services.report_service import ReportService
from backend.services.task_query_service import TaskQueryService
from backend.services.task_result_service import TaskResultService
from backend.services.task_service import TaskService
from backend.workers.contracts import TaskResult, TaskType, WorkerTaskStatus
from backend.workers.executors.report_executor import ReportExecutor
from backend.workers.task_runner import TaskRunner
from backend.workers.task_submitter import TaskSubmitter
from intranet_app.app import IntranetApp
from intranet_app.auth import PasswordHash
from intranet_app.domain import ProcessingResult
from intranet_app.storage import AutomationRunRecord, AutomationTaskRecord, UserRecord


class DailyReportTaskMigrationTests(unittest.TestCase):
    def test_legacy_mode_keeps_existing_result_payload(self) -> None:
        app = object.__new__(IntranetApp)
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "uploads").mkdir()
            (root / "results").mkdir()
            app.config = SimpleNamespace(upload_dir=root / "uploads", result_dir=root / "results")
            app.storage = _Storage()
            sent: dict[str, object] = {}
            calls: list[str] = []
            selected_file = SimpleNamespace(path=root / "source.csv", start_date="20260725", end_date="20260725", rows=[{"a": "b"}])
            result = ProcessingResult(
                module="anta_meituan_reporting",
                output_rows=[{"metric": "sales", "value": "100"}],
                summary={"sales": "100"},
                warnings=[],
            )
            app._read_urlencoded = lambda handler: {"report_date": ["2026-07-25"]}
            app._selected_meituan_report_date = lambda fields: "20260725"
            app._sync_meituan_download_sources = lambda: calls.append("sync") or []
            app._ingest_meituan_plugin_files_to_foundation = lambda username: calls.append("ingest") or 1
            app._load_anta_meituan_sources_from_foundation = lambda report_type, selected_date: ({}, {"product": selected_file})
            app._result_page = lambda user, job_id, processing_result: f"legacy:{job_id}:{processing_result.output_rows[0]['value']}"
            app._send_html = lambda handler, content, status=200: sent.update({"content": content, "status": status})
            app._submit_anta_meituan_daily_report_task = _should_not_call

            with patch("intranet_app.app._report_task_mode", return_value="legacy"):
                with patch("intranet_app.app.anta_meituan_reporting.build_meituan_daily_report", return_value=result):
                    app._handle_anta_meituan_reporting_run(object(), _user(), "daily")

            self.assertEqual(calls, ["sync", "ingest"])
            self.assertEqual(sent["content"], "legacy:11:100")
            self.assertEqual(sent["status"], 200)
            self.assertTrue(list((root / "results").glob("*_anta_meituan_daily_report.csv")))

    def test_task_mode_submits_daily_report_task(self) -> None:
        app = object.__new__(IntranetApp)
        sent: dict[str, object] = {}
        task_result = TaskResult(
            task_id=8,
            status=WorkerTaskStatus.SUCCESS,
            result={"module": "anta_meituan_reporting"},
            error="",
            finished_time="2026-08-03T10:00:00+00:00",
        )
        submitted: list[str] = []
        app._read_urlencoded = lambda handler: {"report_date": ["2026-07-25"]}
        app._selected_meituan_report_date = lambda fields: "20260725"
        app._submit_anta_meituan_daily_report_task = lambda report_date, user: submitted.append(report_date) or task_result
        app._task_result_page = lambda user, result: f"task:{result.task_id}:{result.status.value}"
        app._send_html = lambda handler, content, status=200: sent.update({"content": content, "status": status})
        app._sync_meituan_download_sources = _should_not_call

        with patch("intranet_app.app._report_task_mode", return_value="task"):
            app._handle_anta_meituan_reporting_run(object(), _user(), "daily")

        self.assertEqual(submitted, ["20260725"])
        self.assertEqual(sent["content"], "task:8:success")

    def test_report_executor_generates_csv_result_asset(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = _report_executor(Path(temp_dir), _FoundationRepository())
            payload = build_daily_report_task_payload("20260725", _user())
            result = service._build_report(payload)

            self.assertEqual(result.summary["\u9500\u552e\u989d"], "100.00")

            task_result = service._execute(_task_request(1, payload))

            self.assertEqual(task_result.status, WorkerTaskStatus.SUCCESS)
            asset = task_result.result["result_asset"]
            self.assertEqual(asset["filename"], "1_anta_kids_meituan_daily_20260725_report.csv")
            self.assertTrue(Path(str(asset["file_path"])).exists())
            with Path(str(asset["file_path"])).open("r", encoding="utf-8-sig", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(rows[0]["\u62a5\u8868\u7c7b\u578b"], "\u65e5\u62a5")

    def test_task_result_service_can_download_generated_task_asset(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result_root = Path(temp_dir)
            repository = _TaskRepository()
            submitter = _submitter(repository, result_root, _FoundationRepository())
            task_result = submitter.submit(TaskType.REPORT_GENERATE, build_daily_report_task_payload("20260725", _user()), "admin")
            query = TaskQueryService(repository)
            result_service = TaskResultService(query, result_root)

            info = result_service.get_download_info(task_result.task_id)

            self.assertTrue(info.path.exists())
            self.assertEqual(info.filename, "1_anta_kids_meituan_daily_20260725_report.csv")

    def test_failed_task_status_is_saved_when_executor_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repository = _TaskRepository()
            submitter = _submitter(repository, Path(temp_dir), _EmptyFoundationRepository())

            task_result = submitter.submit(TaskType.REPORT_GENERATE, build_daily_report_task_payload("20260725", _user()), "admin")

            self.assertEqual(task_result.status, WorkerTaskStatus.FAILED)
            self.assertEqual(repository.runs[-1].status, "failed")
            self.assertIn("基础数据层缺少商品/订单数据", repository.runs[-1].message)


def _submitter(repository: _TaskRepository, result_root: Path, foundation: FoundationRepository) -> TaskSubmitter:
    report_service = ReportService(foundation)
    asset_service = ResultAssetService(LocalStorageProvider(result_root))
    executor = ReportExecutor(report_service, asset_service)
    runner = TaskRunner({TaskType.REPORT_GENERATE: executor})
    return TaskSubmitter(TaskService(repository), runner)


def _report_executor(result_root: Path, foundation: FoundationRepository) -> ReportExecutor:
    return ReportExecutor(ReportService(foundation), ResultAssetService(LocalStorageProvider(result_root)))


def _task_request(task_id: int, payload: dict[str, str]):
    from backend.workers.contracts import TaskRequest

    return TaskRequest(
        task_id=task_id,
        task_type=TaskType.REPORT_GENERATE,
        created_by="admin",
        payload=payload,
        created_time="2026-08-03T10:00:00+00:00",
    )


class _FoundationRepository(FoundationRepository):
    def save_foundation_check(self, record):
        raise NotImplementedError

    def save_foundation_rows(self, import_batch_id: str, plan):
        raise NotImplementedError

    def query_foundation_rows(self, brand_id: str, platform: str, channel: str, file_type: str) -> list[dict[str, str]]:
        if file_type == "product_order":
            return [
                {
                    "\u65e5\u671f": "20260725",
                    "\u8ba2\u5355\u7f16\u53f7": "order-1",
                    "\u5e97\u94fa\u540d\u79f0": "store-xian",
                    "\u5e97\u94faID": "store-1",
                    "\u5e97\u94fa\u6240\u5728\u57ce\u5e02": "xian",
                    "\u8ba2\u5355\u72b6\u6001": "\u5df2\u5b8c\u6210",
                    "\u5546\u54c1\u5206\u7c7b": "shoes",
                    "\u5546\u54c1\u540d\u79f0": "UFO shoes",
                    "\u5546\u54c1\u9500\u552e\u6570\u91cf": "1",
                    "\u5546\u54c1\u5b9e\u4ed8\u9500\u552e\u989d": "100",
                }
            ]
        return []


class _EmptyFoundationRepository(_FoundationRepository):
    def query_foundation_rows(self, brand_id: str, platform: str, channel: str, file_type: str) -> list[dict[str, str]]:
        return []


class _TaskRepository(TaskRepository):
    def __init__(self) -> None:
        self.tasks: list[AutomationTaskRecord] = []
        self.runs: list[AutomationRunRecord] = []

    def create_task(self, request: AutomationTaskCreate) -> int:
        task_id = len(self.tasks) + 1
        self.tasks.append(
            AutomationTaskRecord(
                id=task_id,
                task_name=request.task_name,
                business_unit=request.business_unit,
                brand_id=request.brand_id,
                brand_name=request.brand_name,
                platform=request.platform,
                channel=request.channel,
                file_type=request.file_type,
                frequency=request.frequency,
                scheduled_time=request.scheduled_time,
                date_window=request.date_window,
                enabled=request.enabled,
                output_folder=request.output_folder,
                owner=request.owner,
                notes=request.notes,
                created_at="2026-08-03T10:00:00+08:00",
                updated_at="2026-08-03T10:01:00+08:00",
            )
        )
        return task_id

    def update_task_status(self, task_id: int, status: str) -> None:
        return None

    def get_task(self, task_id: int) -> AutomationTaskRecord | None:
        for task in self.tasks:
            if task.id == task_id:
                return task
        return None

    def save_task_result(self, request: TaskRunCreate) -> int:
        run_id = len(self.runs) + 1
        message = request.result_message if request.result_message else f"error: {request.error_message}"
        self.runs.append(
            AutomationRunRecord(
                id=run_id,
                task_id=request.task_id,
                task_name=f"Task {request.task_id}",
                run_date=request.run_date,
                status=request.status,
                downloaded_file_count=0,
                synced_file_count=0,
                message=message,
                executed_by=request.executed_by,
                created_at="2026-08-03T10:02:00+08:00",
            )
        )
        return run_id

    def list_tasks(self) -> list[AutomationTaskRecord]:
        return list(self.tasks)

    def list_task_runs(self, limit: int = 200) -> list[AutomationRunRecord]:
        return list(self.runs[:limit])


class _Storage:
    def save_job(self, **kwargs: object) -> int:
        return 11


def _should_not_call(*args: object, **kwargs: object) -> None:
    raise AssertionError("unexpected legacy path call")


def _user() -> UserRecord:
    return UserRecord(
        id=1,
        username="admin",
        display_name="Admin",
        role="admin",
        password_hash=PasswordHash("salt", "digest"),
    )


if __name__ == "__main__":
    unittest.main()
