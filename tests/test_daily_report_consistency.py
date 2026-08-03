from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from backend.adapters.report_task_adapter import build_daily_report_task_payload
from backend.repositories.interfaces import AutomationTaskCreate, FoundationRepository, TaskRepository, TaskRunCreate
from backend.services.assets.asset_service import ResultAssetService
from backend.services.assets.providers.local_provider import LocalStorageProvider
from backend.services.report_service import ReportService
from backend.services.task_query_service import TaskQueryService
from backend.services.task_result_service import TaskResultService
from backend.services.task_service import TaskService
from backend.workers.contracts import TaskType, WorkerTaskStatus
from backend.workers.executors.report_executor import ReportExecutor
from backend.workers.task_runner import TaskRunner
from backend.workers.task_submitter import TaskSubmitter
from intranet_app.auth import PasswordHash
from intranet_app.io_utils import write_csv
from intranet_app.processors import anta_meituan_reporting
from intranet_app.storage import AutomationRunRecord, AutomationTaskRecord, UserRecord


REPORT_DATE = "20260725"
HEADERS = ("\u62a5\u8868\u7c7b\u578b", "\u677f\u5757", "\u6392\u5e8f", "\u540d\u79f0", "\u6570\u503c", "\u8bf4\u660e")
FIELD_REPORT_TYPE = "\u62a5\u8868\u7c7b\u578b"
FIELD_SECTION = "\u677f\u5757"
FIELD_NAME = "\u540d\u79f0"
FIELD_VALUE = "\u6570\u503c"
SECTION_CORE = "\u6838\u5fc3\u6307\u6807"
SECTION_STORE_TOP = "\u8fd17\u5929TOP\u95e8\u5e97"
SECTION_PRODUCT_TOP = "\u8fd17\u5929TOP\u5546\u54c1"
NAME_SALES = "\u9500\u552e\u989d"
NAME_QUANTITY = "\u9500\u91cf"


class DailyReportConsistencyTests(unittest.TestCase):
    def test_legacy_and_task_daily_report_outputs_are_consistent(self) -> None:
        foundation = _FoundationRepository()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            legacy_path = root / "legacy_anta_meituan_daily_report.csv"
            task_result_root = root / "task_results"

            legacy_result = anta_meituan_reporting.build_meituan_daily_report(_sources_from(foundation), REPORT_DATE)
            write_csv(legacy_path, legacy_result.output_rows)
            legacy_rows = _read_csv_rows(legacy_path)

            repository = _TaskRepository()
            submitter = _submitter(repository, task_result_root, foundation)
            task_result = submitter.submit(TaskType.REPORT_GENERATE, build_daily_report_task_payload(REPORT_DATE, _user()), "admin")
            self.assertEqual(task_result.status, WorkerTaskStatus.SUCCESS)
            self.assertIn("result_asset", task_result.result)

            result_service = TaskResultService(TaskQueryService(repository), task_result_root)
            download_info = result_service.get_download_info(task_result.task_id)
            task_rows = _read_csv_rows(download_info.path)

            self.assertTrue(legacy_path.exists())
            self.assertTrue(download_info.path.exists())
            self.assertTrue(legacy_path.name.endswith(".csv"))
            self.assertTrue(download_info.filename.endswith(".csv"))
            self.assertEqual(len(legacy_rows), len(task_rows))
            self.assertEqual(_headers(legacy_rows), _headers(task_rows))
            self.assertEqual(len(_headers(legacy_rows)), len(HEADERS))
            self.assertEqual(_core_values(legacy_result.summary, legacy_rows), _core_values(task_result.result["summary"], task_rows))
            self.assertEqual(legacy_rows, task_rows)


def _submitter(repository: _TaskRepository, result_root: Path, foundation: FoundationRepository) -> TaskSubmitter:
    report_service = ReportService(foundation)
    asset_service = ResultAssetService(LocalStorageProvider(result_root))
    executor = ReportExecutor(report_service, asset_service)
    runner = TaskRunner({TaskType.REPORT_GENERATE: executor})
    return TaskSubmitter(TaskService(repository), runner)


def _sources_from(foundation: FoundationRepository) -> anta_meituan_reporting.MeituanReportSources:
    return anta_meituan_reporting.MeituanReportSources(
        product_rows=foundation.query_foundation_rows("anta_kids", "meituan", "instant_retail", "product_order"),
        finance_rows=foundation.query_foundation_rows("anta_kids", "meituan", "instant_retail", "store_finance"),
        traffic_rows=foundation.query_foundation_rows("anta_kids", "meituan", "instant_retail", "store_traffic"),
        review_rows=foundation.query_foundation_rows("anta_kids", "meituan", "instant_retail", "service_review"),
    )


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not isinstance(path, Path):
        raise TypeError("path must be pathlib.Path")
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise AssertionError("csv rows must not be empty")
    return rows


def _headers(rows: list[dict[str, str]]) -> tuple[str, ...]:
    if not rows:
        raise AssertionError("rows must not be empty")
    result = tuple(rows[0].keys())
    if not result:
        raise AssertionError("headers must not be empty")
    return result


def _core_values(summary: dict[str, object], rows: list[dict[str, str]]) -> dict[str, object]:
    if not isinstance(summary, dict):
        raise TypeError("summary must be dict")
    result = {
        "date": str(summary.get("\u7ed3\u675f\u65e5\u671f", "")),
        "store": _first_value(rows, SECTION_STORE_TOP, FIELD_NAME),
        "product": _first_value(rows, SECTION_PRODUCT_TOP, FIELD_NAME),
        "amount": _metric_value(rows, NAME_SALES),
        "quantity": _metric_value(rows, NAME_QUANTITY),
    }
    assert result["date"] == REPORT_DATE
    return result


def _first_value(rows: list[dict[str, str]], section: str, field_name: str) -> str:
    for row in rows:
        if row.get(FIELD_SECTION) == section:
            value = row.get(field_name, "")
            if value:
                return value
    raise AssertionError(f"missing section value: {section}")


def _metric_value(rows: list[dict[str, str]], metric_name: str) -> str:
    for row in rows:
        if row.get(FIELD_SECTION) == SECTION_CORE and row.get(FIELD_NAME) == metric_name:
            value = row.get(FIELD_VALUE, "")
            if value:
                return value
    raise AssertionError(f"missing metric: {metric_name}")


class _FoundationRepository(FoundationRepository):
    def save_foundation_check(self, record):
        raise NotImplementedError

    def save_foundation_rows(self, import_batch_id: str, plan):
        raise NotImplementedError

    def query_foundation_rows(self, brand_id: str, platform: str, channel: str, file_type: str) -> list[dict[str, str]]:
        if file_type == "product_order":
            return _product_rows()
        if file_type == "store_finance":
            return _finance_rows()
        if file_type == "store_traffic":
            return _traffic_rows()
        if file_type == "service_review":
            return []
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


def _product_rows() -> list[dict[str, str]]:
    return [
        {
            "\u65e5\u671f": REPORT_DATE,
            "\u8ba2\u5355\u7f16\u53f7": "order-1",
            "\u5e97\u94fa\u540d\u79f0": "store-xian",
            "\u5e97\u94faID": "store-1",
            "\u5e97\u94fa\u6240\u5728\u57ce\u5e02": "xian",
            "\u8ba2\u5355\u72b6\u6001": "\u5df2\u5b8c\u6210",
            "\u5546\u54c1\u5206\u7c7b": "shoes",
            "\u5546\u54c1\u540d\u79f0": "UFO shoes",
            "\u5546\u54c1\u9500\u552e\u6570\u91cf": "2",
            "\u5546\u54c1\u5b9e\u4ed8\u9500\u552e\u989d": "200",
        },
        {
            "\u65e5\u671f": REPORT_DATE,
            "\u8ba2\u5355\u7f16\u53f7": "order-2",
            "\u5e97\u94fa\u540d\u79f0": "store-hangzhou",
            "\u5e97\u94faID": "store-2",
            "\u5e97\u94fa\u6240\u5728\u57ce\u5e02": "hangzhou",
            "\u8ba2\u5355\u72b6\u6001": "\u5df2\u5b8c\u6210",
            "\u5546\u54c1\u5206\u7c7b": "swimwear",
            "\u5546\u54c1\u540d\u79f0": "Swim suit",
            "\u5546\u54c1\u9500\u552e\u6570\u91cf": "1",
            "\u5546\u54c1\u5b9e\u4ed8\u9500\u552e\u989d": "100",
        },
    ]


def _finance_rows() -> list[dict[str, str]]:
    return [
        {
            "\u5f00\u59cb\u65f6\u95f4": REPORT_DATE,
            "\u7ed3\u675f\u65f6\u95f4": REPORT_DATE,
            "\u5546\u5bb6ID": "store-1",
            "\u5546\u5bb6\u540d\u79f0": "store-xian",
            "\u7701\u4efd": "shaanxi",
            "\u57ce\u5e02": "xian",
            "\u5b9e\u4ed8\u4ea4\u6613\u989d": "200",
            "\u6709\u6548\u8ba2\u5355\u6570": "1",
        },
        {
            "\u5f00\u59cb\u65f6\u95f4": REPORT_DATE,
            "\u7ed3\u675f\u65f6\u95f4": REPORT_DATE,
            "\u5546\u5bb6ID": "store-2",
            "\u5546\u5bb6\u540d\u79f0": "store-hangzhou",
            "\u7701\u4efd": "zhejiang",
            "\u57ce\u5e02": "hangzhou",
            "\u5b9e\u4ed8\u4ea4\u6613\u989d": "100",
            "\u6709\u6548\u8ba2\u5355\u6570": "1",
        },
    ]


def _traffic_rows() -> list[dict[str, str]]:
    return [
        {
            "\u5f00\u59cb\u65f6\u95f4": REPORT_DATE,
            "\u7ed3\u675f\u65f6\u95f4": REPORT_DATE,
            "\u5546\u5bb6ID": "store-1",
            "\u5546\u5bb6\u540d\u79f0": "store-xian",
            "\u57ce\u5e02": "xian",
            "\u66dd\u5149\u4eba\u6570": "1000",
            "\u5165\u5e97\u4eba\u6570": "100",
            "\u4e0b\u5355\u4eba\u6570": "20",
            "\u5165\u5e97\u8f6c\u5316\u7387": "10%",
            "\u4e0b\u5355\u8f6c\u5316\u7387": "20%",
        }
    ]


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
