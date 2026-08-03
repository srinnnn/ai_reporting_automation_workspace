from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path

from backend.adapters.report_task_adapter import build_daily_report_task_payload
from backend.repositories.interfaces import AutomationTaskCreate, FoundationRepository, TaskRepository, TaskRunCreate
from backend.repositories.sqlite.foundation_repository import SQLiteFoundationRepository
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
from intranet_app.config import DEFAULT_CONFIG
from intranet_app.io_utils import write_csv
from intranet_app.processors import anta_meituan_reporting
from intranet_app.storage import AppStorage, AutomationRunRecord, AutomationTaskRecord


REPORT_HEADERS = (
    "\u65e5\u671f",
    "legacy_status",
    "task_status",
    "legacy_rows",
    "task_rows",
    "row_delta",
    "amount_delta",
    "field_diff",
    "result",
    "message",
)
FIELD_SECTION = "\u677f\u5757"
FIELD_NAME = "\u540d\u79f0"
FIELD_VALUE = "\u6570\u503c"
SECTION_CORE = "\u6838\u5fc3\u6307\u6807"
SECTION_STORE_TOP = "\u8fd17\u5929TOP\u95e8\u5e97"
SECTION_PRODUCT_TOP = "\u8fd17\u5929TOP\u5546\u54c1"
NAME_SALES = "\u9500\u552e\u989d"
NAME_QUANTITY = "\u9500\u91cf"
SUMMARY_END_DATE = "\u7ed3\u675f\u65e5\u671f"


@dataclass(frozen=True)
class BatchConsistencyRow:
    date: str
    legacy_status: str
    task_status: str
    legacy_rows: int
    task_rows: int
    row_delta: int
    amount_delta: str
    field_diff: str
    result: str
    message: str

    def __post_init__(self) -> None:
        if not isinstance(self.date, str) or not self.date.strip():
            raise ValueError("date must not be empty")
        for field_name, field_value in (
            ("legacy_status", self.legacy_status),
            ("task_status", self.task_status),
            ("amount_delta", self.amount_delta),
            ("field_diff", self.field_diff),
            ("result", self.result),
            ("message", self.message),
        ):
            if not isinstance(field_value, str):
                raise TypeError(f"{field_name} must be str")
        for field_name, field_value in (("legacy_rows", self.legacy_rows), ("task_rows", self.task_rows), ("row_delta", self.row_delta)):
            if not isinstance(field_value, int):
                raise TypeError(f"{field_name} must be int")
        if self.result not in {"PASS", "FAIL"}:
            raise ValueError("result must be PASS or FAIL")

    def to_row(self) -> dict[str, str]:
        row = {
            "\u65e5\u671f": self.date,
            "legacy_status": self.legacy_status,
            "task_status": self.task_status,
            "legacy_rows": str(self.legacy_rows),
            "task_rows": str(self.task_rows),
            "row_delta": str(self.row_delta),
            "amount_delta": self.amount_delta,
            "field_diff": self.field_diff,
            "result": self.result,
            "message": self.message,
        }
        assert tuple(row.keys()) == REPORT_HEADERS
        return row


@dataclass(frozen=True)
class BatchConsistencyReport:
    rows: tuple[BatchConsistencyRow, ...]
    output_path: Path

    def __post_init__(self) -> None:
        if not isinstance(self.rows, tuple):
            raise TypeError("rows must be tuple")
        if not isinstance(self.output_path, Path):
            raise TypeError("output_path must be pathlib.Path")

    @property
    def passed(self) -> bool:
        return all(row.result == "PASS" for row in self.rows)


def run_batch_consistency(
    start_date: str,
    end_date: str,
    foundation_repository: FoundationRepository,
    output_dir: Path,
    created_by: str = "consistency",
) -> BatchConsistencyReport:
    if not isinstance(foundation_repository, FoundationRepository):
        raise TypeError("foundation_repository must be FoundationRepository")
    if not isinstance(output_dir, Path):
        raise TypeError("output_dir must be pathlib.Path")
    if not isinstance(created_by, str) or not created_by.strip():
        raise ValueError("created_by must not be empty")
    dates = _date_range(start_date, end_date)
    output_dir.mkdir(parents=True, exist_ok=True)
    daily_dir = output_dir / "daily"
    daily_dir.mkdir(parents=True, exist_ok=True)
    rows = tuple(_check_one_day(date_value, foundation_repository, daily_dir, created_by.strip()) for date_value in dates)
    output_path = output_dir / f"anta_meituan_daily_consistency_{dates[0]}_{dates[-1]}.csv"
    write_csv(output_path, [row.to_row() for row in rows])
    report = BatchConsistencyReport(rows=rows, output_path=output_path)
    assert report.output_path.exists()
    return report


def build_sqlite_foundation_repository(database_path: Path | None = None) -> SQLiteFoundationRepository:
    if database_path is not None and not isinstance(database_path, Path):
        raise TypeError("database_path must be pathlib.Path")
    storage = AppStorage(database_path if database_path is not None else DEFAULT_CONFIG.database_path)
    repository = SQLiteFoundationRepository(storage)
    assert isinstance(repository, SQLiteFoundationRepository)
    return repository


def main() -> int:
    parser = argparse.ArgumentParser(description="Batch consistency check for Anta Meituan daily reports.")
    parser.add_argument("--start-date", required=True, help="Start date in YYYYMMDD or YYYY-MM-DD.")
    parser.add_argument("--end-date", required=True, help="End date in YYYYMMDD or YYYY-MM-DD.")
    parser.add_argument("--output-dir", default="runtime/consistency_reports", help="Output directory for CSV reports.")
    parser.add_argument("--database-path", default="", help="Optional local SQLite database path.")
    args = parser.parse_args()

    database_path = Path(args.database_path).resolve() if args.database_path.strip() else None
    repository = build_sqlite_foundation_repository(database_path)
    report = run_batch_consistency(args.start_date, args.end_date, repository, Path(args.output_dir).resolve())
    print(json.dumps({"output_path": str(report.output_path), "passed": report.passed, "rows": len(report.rows)}, ensure_ascii=False))
    return 0 if report.passed else 1


def _check_one_day(date_value: str, foundation_repository: FoundationRepository, output_dir: Path, created_by: str) -> BatchConsistencyRow:
    try:
        legacy_path = output_dir / f"legacy_{date_value}.csv"
        task_root = output_dir / f"task_{date_value}"
        legacy_result = anta_meituan_reporting.build_meituan_daily_report(_sources_from(foundation_repository), date_value)
        write_csv(legacy_path, legacy_result.output_rows)
        legacy_rows = _read_csv_rows(legacy_path)

        task_repository = _InMemoryTaskRepository()
        submitter = _submitter(task_repository, task_root, foundation_repository)
        task_result = submitter.submit(TaskType.REPORT_GENERATE, build_daily_report_task_payload(date_value, _SystemUser(created_by)), created_by)
        task_status = task_result.status.value
        result_service = TaskResultService(TaskQueryService(task_repository), task_root)
        download_info = result_service.get_download_info(task_result.task_id)
        task_rows = _read_csv_rows(download_info.path)

        field_diff = _field_diff(legacy_rows, task_rows)
        amount_delta = _amount_delta(legacy_rows, task_rows)
        row_delta = len(task_rows) - len(legacy_rows)
        messages = _comparison_messages(legacy_result.summary, task_result.result, legacy_rows, task_rows, field_diff, amount_delta, task_result.status)
        result = "PASS" if not messages else "FAIL"
        return BatchConsistencyRow(
            date=date_value,
            legacy_status="success",
            task_status=task_status,
            legacy_rows=len(legacy_rows),
            task_rows=len(task_rows),
            row_delta=row_delta,
            amount_delta=amount_delta,
            field_diff=field_diff,
            result=result,
            message="; ".join(messages),
        )
    except (AssertionError, OSError, TypeError, ValueError, RuntimeError, KeyError) as exc:
        return BatchConsistencyRow(
            date=date_value,
            legacy_status="failed",
            task_status="failed",
            legacy_rows=0,
            task_rows=0,
            row_delta=0,
            amount_delta="",
            field_diff="",
            result="FAIL",
            message=f"{type(exc).__name__}: {exc}",
        )


def _submitter(repository: TaskRepository, result_root: Path, foundation_repository: FoundationRepository) -> TaskSubmitter:
    report_service = ReportService(foundation_repository)
    asset_service = ResultAssetService(LocalStorageProvider(result_root))
    executor = ReportExecutor(report_service, asset_service)
    runner = TaskRunner({TaskType.REPORT_GENERATE: executor})
    submitter = TaskSubmitter(TaskService(repository), runner)
    assert isinstance(submitter, TaskSubmitter)
    return submitter


def _sources_from(foundation_repository: FoundationRepository) -> anta_meituan_reporting.MeituanReportSources:
    return anta_meituan_reporting.MeituanReportSources(
        product_rows=foundation_repository.query_foundation_rows("anta_kids", "meituan", "instant_retail", "product_order"),
        finance_rows=foundation_repository.query_foundation_rows("anta_kids", "meituan", "instant_retail", "store_finance"),
        traffic_rows=foundation_repository.query_foundation_rows("anta_kids", "meituan", "instant_retail", "store_traffic"),
        review_rows=foundation_repository.query_foundation_rows("anta_kids", "meituan", "instant_retail", "service_review"),
    )


def _comparison_messages(
    legacy_summary: dict[str, str],
    task_result: dict[str, object],
    legacy_rows: list[dict[str, str]],
    task_rows: list[dict[str, str]],
    field_diff: str,
    amount_delta: str,
    task_status: WorkerTaskStatus,
) -> list[str]:
    messages: list[str] = []
    if task_status != WorkerTaskStatus.SUCCESS:
        messages.append("task status is not success")
    if "result_asset" not in task_result:
        messages.append("result_asset missing")
    if len(legacy_rows) != len(task_rows):
        messages.append("row count mismatch")
    if field_diff:
        messages.append("csv header mismatch")
    if amount_delta != "0.00":
        messages.append("amount mismatch")
    task_summary = task_result.get("summary") if isinstance(task_result.get("summary"), dict) else {}
    if _core_values(legacy_summary, legacy_rows) != _core_values(task_summary, task_rows):
        messages.append("core values mismatch")
    if legacy_rows != task_rows:
        messages.append("row payload mismatch")
    return messages


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


def _field_diff(legacy_rows: list[dict[str, str]], task_rows: list[dict[str, str]]) -> str:
    legacy_headers = _headers(legacy_rows)
    task_headers = _headers(task_rows)
    if legacy_headers == task_headers:
        return ""
    return f"legacy={','.join(legacy_headers)} task={','.join(task_headers)}"


def _amount_delta(legacy_rows: list[dict[str, str]], task_rows: list[dict[str, str]]) -> str:
    delta = _decimal(_metric_value(task_rows, NAME_SALES)) - _decimal(_metric_value(legacy_rows, NAME_SALES))
    return f"{delta:.2f}"


def _core_values(summary: dict[str, object], rows: list[dict[str, str]]) -> dict[str, object]:
    if not isinstance(summary, dict):
        raise TypeError("summary must be dict")
    result = {
        "date": str(summary.get(SUMMARY_END_DATE, "")),
        "store": _first_value(rows, SECTION_STORE_TOP, FIELD_NAME),
        "product": _first_value(rows, SECTION_PRODUCT_TOP, FIELD_NAME),
        "amount": _metric_value(rows, NAME_SALES),
        "quantity": _metric_value(rows, NAME_QUANTITY),
    }
    assert result["date"]
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


def _decimal(value: str) -> Decimal:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("decimal value must not be empty")
    try:
        result = Decimal(value.replace(",", ""))
    except InvalidOperation as exc:
        raise ValueError("decimal value is invalid") from exc
    return result


def _date_range(start_date: str, end_date: str) -> tuple[str, ...]:
    start = _parse_date(start_date)
    end = _parse_date(end_date)
    if start > end:
        raise ValueError("start_date must not be later than end_date")
    dates: list[str] = []
    current = start
    while current <= end:
        dates.append(current.strftime("%Y%m%d"))
        current += timedelta(days=1)
    result = tuple(dates)
    assert result
    return result


def _parse_date(value: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("date must not be empty")
    text = value.strip()
    if len(text) == 8 and text.isdigit():
        return datetime.strptime(text, "%Y%m%d")
    if len(text) == 10 and text[4] == "-" and text[7] == "-":
        return datetime.strptime(text, "%Y-%m-%d")
    raise ValueError("date must use YYYYMMDD or YYYY-MM-DD")


@dataclass(frozen=True)
class _SystemUser:
    username: str

    def __post_init__(self) -> None:
        if not isinstance(self.username, str) or not self.username.strip():
            raise ValueError("username must not be empty")


class _InMemoryTaskRepository(TaskRepository):
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


if __name__ == "__main__":
    raise SystemExit(main())
