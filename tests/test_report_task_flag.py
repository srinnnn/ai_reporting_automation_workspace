from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from backend.core.config import load_core_config
from backend.workers.contracts import TaskResult, WorkerTaskStatus
from intranet_app.app import IntranetApp
from intranet_app.auth import PasswordHash
from intranet_app.domain import ProcessingResult
from intranet_app.storage import UserRecord


class ReportTaskFlagConfigTests(unittest.TestCase):
    def test_default_mode_is_legacy(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config = load_core_config(environ={}, root_dir=Path(temp_dir))

        self.assertEqual(config.report_task_mode, "legacy")

    def test_explicit_legacy_mode(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config = load_core_config(environ={"REPORT_TASK_MODE": "legacy"}, root_dir=Path(temp_dir))

        self.assertEqual(config.report_task_mode, "legacy")

    def test_explicit_task_mode(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config = load_core_config(environ={"REPORT_TASK_MODE": "task"}, root_dir=Path(temp_dir))

        self.assertEqual(config.report_task_mode, "task")

    def test_invalid_mode_falls_back_to_legacy(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config = load_core_config(environ={"REPORT_TASK_MODE": "invalid"}, root_dir=Path(temp_dir))

        self.assertEqual(config.report_task_mode, "legacy")


class ReportTaskFlagAppTests(unittest.TestCase):
    def test_task_mode_uses_task_submit_path_for_daily_report(self) -> None:
        app = object.__new__(IntranetApp)
        sent: dict[str, object] = {}
        task_result = TaskResult(
            task_id=7,
            status=WorkerTaskStatus.SUCCESS,
            result={"module": "anta_meituan_reporting"},
            error="",
            finished_time="2026-07-30T10:00:00+00:00",
        )

        app._read_urlencoded = lambda handler: {"report_date": ["2026-07-25"]}
        app._selected_meituan_report_date = lambda fields: "20260725"
        app._submit_anta_meituan_daily_report_task = lambda report_date, user: task_result
        app._task_result_page = lambda user, result: "task page"
        app._send_html = lambda handler, content, status=200: sent.update({"content": content, "status": status})
        app._sync_meituan_download_sources = _should_not_call

        with patch("intranet_app.app._report_task_mode", return_value="task"):
            app._handle_anta_meituan_reporting_run(object(), _user(), "daily")

        self.assertEqual(sent["content"], "task page")
        self.assertEqual(sent["status"], 200)

    def test_legacy_mode_keeps_existing_daily_flow(self) -> None:
        app = object.__new__(IntranetApp)
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "uploads").mkdir()
            (root / "results").mkdir()
            app.config = SimpleNamespace(upload_dir=root / "uploads", result_dir=root / "results")
            app.storage = _Storage()
            calls: list[str] = []
            sent: dict[str, object] = {}
            selected_file = SimpleNamespace(path=root / "source.csv", start_date="20260725", end_date="20260725", rows=[{"a": "b"}])
            result = ProcessingResult(
                module="anta_meituan_reporting",
                output_rows=[{"metric": "sales", "value": "1"}],
                summary={"rows": "1"},
                warnings=[],
            )

            app._read_urlencoded = lambda handler: {"report_date": ["2026-07-25"]}
            app._selected_meituan_report_date = lambda fields: "20260725"
            app._sync_meituan_download_sources = lambda: calls.append("sync") or []
            app._ingest_meituan_plugin_files_to_foundation = lambda username: calls.append("ingest") or 1
            app._load_anta_meituan_sources_from_foundation = lambda report_type, selected_date: ({}, {"product": selected_file})
            app._result_page = lambda user, job_id, processing_result: "legacy page"
            app._send_html = lambda handler, content, status=200: sent.update({"content": content, "status": status})
            app._submit_anta_meituan_daily_report_task = _should_not_call

            with patch("intranet_app.app._report_task_mode", return_value="legacy"):
                with patch("intranet_app.app.anta_meituan_reporting.build_meituan_daily_report", return_value=result):
                    app._handle_anta_meituan_reporting_run(object(), _user(), "daily")

        self.assertEqual(calls, ["sync", "ingest"])
        self.assertEqual(sent["content"], "legacy page")
        self.assertEqual(sent["status"], 200)


def _should_not_call(*args: object, **kwargs: object) -> None:
    raise AssertionError("legacy sync flow should not run in task mode")


class _Storage:
    def save_job(self, **kwargs: object) -> int:
        return 9


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
