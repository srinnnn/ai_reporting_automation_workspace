from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from backend.adapters.report_task_adapter import build_daily_report_task_payload
from backend.repositories.interfaces import AutomationTaskCreate, FoundationRepository, TaskRepository, TaskRunCreate
from backend.services.assets.asset_service import ResultAssetService
from backend.services.assets.providers.local_provider import LocalStorageProvider
from backend.services.permission_service import PermissionService
from backend.services.report_service import ReportService
from backend.services.task_console_service import TaskConsoleFilters, TaskConsoleService
from backend.services.task_query_service import TaskQueryService
from backend.services.task_result_service import TaskResultService
from backend.services.task_service import TaskService
from backend.workers.contracts import TaskType, WorkerTaskStatus
from backend.workers.executors.report_executor import ReportExecutor
from backend.workers.task_runner import TaskRunner
from backend.workers.task_submitter import TaskSubmitter
from intranet_app.auth import PasswordHash
from intranet_app.storage import AutomationRunRecord, AutomationTaskRecord, UserRecord


PHASE1_DATES = ("20260720", "20260721", "20260722", "20260723", "20260724", "20260725")


class DailyReportPhase1InternalRolloutTests(unittest.TestCase):
    def test_admin_can_validate_task_mode_daily_reports_for_phase1_dates(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result_root = Path(temp_dir) / "task-results"
            repository = _TaskRepository()
            submitter = _submitter(repository, result_root, _Phase1FoundationRepository())
            admin = _admin_user()

            results = [
                submitter.submit(TaskType.REPORT_GENERATE, build_daily_report_task_payload(report_date, admin), admin.username)
                for report_date in PHASE1_DATES
            ]

            self.assertEqual(len(results), len(PHASE1_DATES))
            self.assertTrue(all(result.status == WorkerTaskStatus.SUCCESS for result in results))
            self.assertTrue(all("result_asset" in result.result for result in results))
            self.assertEqual([run.status for run in repository.runs], ["success"] * len(PHASE1_DATES))

            query = TaskQueryService(repository)
            result_service = TaskResultService(query, result_root)
            console = TaskConsoleService(query, result_service, PermissionService())
            visible = console.list_visible_tasks(admin, TaskConsoleFilters(task_type="REPORT_GENERATE", status="success", created_by="admin"))

            self.assertEqual(visible["total"], len(PHASE1_DATES))
            self.assertEqual({item["task_id"] for item in visible["tasks"]}, {result.task_id for result in results})

            for task_result, report_date in zip(results, PHASE1_DATES):
                detail = console.get_task_detail(admin, task_result.task_id)
                download_info = result_service.get_download_info(task_result.task_id)
                rows = _read_csv_rows(download_info.path)

                self.assertEqual(detail["status"], "success")
                self.assertTrue(detail["downloadable"])
                self.assertEqual(download_info.filename, f"{task_result.task_id}_anta_kids_meituan_daily_{report_date}_report.csv")
                self.assertGreater(len(rows), 0)
                self.assertEqual(_metric_value(rows, "\u9500\u552e\u989d"), "300.00")


def _submitter(repository: _TaskRepository, result_root: Path, foundation: FoundationRepository) -> TaskSubmitter:
    report_service = ReportService(foundation)
    asset_service = ResultAssetService(LocalStorageProvider(result_root))
    executor = ReportExecutor(report_service, asset_service)
    runner = TaskRunner({TaskType.REPORT_GENERATE: executor})
    return TaskSubmitter(TaskService(repository), runner)


class _Phase1FoundationRepository(FoundationRepository):
    def save_foundation_check(self, record):
        raise NotImplementedError

    def save_foundation_rows(self, import_batch_id: str, plan):
        raise NotImplementedError

    def query_foundation_rows(self, brand_id: str, platform: str, channel: str, file_type: str) -> list[dict[str, str]]:
        if brand_id != "anta_kids" or platform != "meituan" or channel != "instant_retail":
            return []
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
                created_at=f"2026-08-03T10:{task_id:02d}:00+08:00",
                updated_at=f"2026-08-03T10:{task_id:02d}:30+08:00",
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
                created_at=f"2026-08-03T10:{run_id:02d}:59+08:00",
            )
        )
        return run_id

    def list_tasks(self) -> list[AutomationTaskRecord]:
        return list(self.tasks)

    def list_task_runs(self, limit: int = 200) -> list[AutomationRunRecord]:
        return list(self.runs[:limit])


def _product_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for date_value in PHASE1_DATES:
        rows.append(_product_row(date_value, f"order-{date_value}-1", "store-xian", "UFO shoes", "2", "200"))
        rows.append(_product_row(date_value, f"order-{date_value}-2", "store-hangzhou", "Swim suit", "1", "100"))
    return rows


def _finance_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for date_value in PHASE1_DATES:
        rows.append(_finance_row(date_value, "store-1", "store-xian", "200", "1"))
        rows.append(_finance_row(date_value, "store-2", "store-hangzhou", "100", "1"))
    return rows


def _traffic_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for date_value in PHASE1_DATES:
        rows.append(_traffic_row(date_value, "store-1", "store-xian"))
        rows.append(_traffic_row(date_value, "store-2", "store-hangzhou"))
    return rows


def _product_row(date_value: str, order_id: str, store_name: str, product_name: str, quantity: str, amount: str) -> dict[str, str]:
    return {
        "\u65e5\u671f": date_value,
        "\u8ba2\u5355\u7f16\u53f7": order_id,
        "\u5e97\u94fa\u540d\u79f0": store_name,
        "\u5e97\u94faID": store_name,
        "\u5e97\u94fa\u6240\u5728\u57ce\u5e02": "city",
        "\u8ba2\u5355\u72b6\u6001": "\u5df2\u5b8c\u6210",
        "\u5546\u54c1\u5206\u7c7b": "category",
        "\u5546\u54c1\u540d\u79f0": product_name,
        "\u5546\u54c1\u9500\u552e\u6570\u91cf": quantity,
        "\u5546\u54c1\u5b9e\u4ed8\u9500\u552e\u989d": amount,
    }


def _finance_row(date_value: str, store_id: str, store_name: str, amount: str, orders: str) -> dict[str, str]:
    return {
        "\u5f00\u59cb\u65f6\u95f4": date_value,
        "\u7ed3\u675f\u65f6\u95f4": date_value,
        "\u5546\u5bb6ID": store_id,
        "\u5546\u5bb6\u540d\u79f0": store_name,
        "\u7701\u4efd": "province",
        "\u57ce\u5e02": "city",
        "\u5b9e\u4ed8\u4ea4\u6613\u989d": amount,
        "\u6709\u6548\u8ba2\u5355\u6570": orders,
    }


def _traffic_row(date_value: str, store_id: str, store_name: str) -> dict[str, str]:
    return {
        "\u5f00\u59cb\u65f6\u95f4": date_value,
        "\u7ed3\u675f\u65f6\u95f4": date_value,
        "\u5546\u5bb6ID": store_id,
        "\u5546\u5bb6\u540d\u79f0": store_name,
        "\u57ce\u5e02": "city",
        "\u66dd\u5149\u4eba\u6570": "1000",
        "\u5165\u5e97\u4eba\u6570": "100",
        "\u4e0b\u5355\u4eba\u6570": "20",
        "\u5165\u5e97\u8f6c\u5316\u7387": "10%",
        "\u4e0b\u5355\u8f6c\u5316\u7387": "20%",
    }


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise AssertionError("csv rows must not be empty")
    return rows


def _metric_value(rows: list[dict[str, str]], metric_name: str) -> str:
    for row in rows:
        if row.get("\u677f\u5757") == "\u6838\u5fc3\u6307\u6807" and row.get("\u540d\u79f0") == metric_name:
            value = row.get("\u6570\u503c", "")
            if value:
                return value
    raise AssertionError(f"missing metric: {metric_name}")


def _admin_user() -> UserRecord:
    return UserRecord(
        id=1,
        username="admin",
        display_name="Admin",
        role="admin",
        password_hash=PasswordHash("salt", "digest"),
    )


if __name__ == "__main__":
    unittest.main()
