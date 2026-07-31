from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from backend.services.result_asset_service import ResultAssetService
from backend.services.report_service import ReportService
from backend.workers.contracts import TaskRequest, TaskType, WorkerTaskStatus
from backend.workers.executors.report_executor import ReportExecutor
from intranet_app.domain import ProcessingResult
from intranet_app.io_utils import write_csv


class ResultAssetServiceTests(unittest.TestCase):
    def test_saves_csv_result_asset(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = ResultAssetService(Path(temp_dir))

            asset = service.save_csv("daily-report.csv", [{"metric": "sales", "value": "100"}])

            self.assertTrue(asset.path.exists())
            self.assertEqual(asset.filename, "daily-report.csv")
            self.assertGreater(asset.size, 0)
            with asset.path.open("r", encoding="utf-8-sig", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(rows, [{"metric": "sales", "value": "100"}])

    def test_creates_missing_output_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "missing" / "results"
            service = ResultAssetService(output_dir)

            asset = service.save_csv("daily-report", [{"metric": "orders", "value": "2"}])

            self.assertTrue(output_dir.exists())
            self.assertEqual(asset.filename, "daily-report.csv")
            self.assertTrue(asset.path.exists())

    def test_report_executor_returns_result_asset_information(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            executor = ReportExecutor(_ReportService())
            task = _report_task(Path(temp_dir))

            result = executor.execute(task)

            self.assertEqual(result.status, WorkerTaskStatus.SUCCESS)
            self.assertIn("result_asset", result.result)
            asset = result.result["result_asset"]
            self.assertIsInstance(asset, dict)
            self.assertEqual(asset["filename"], "2_anta_kids_meituan_daily_20260725_report.csv")
            self.assertTrue(Path(str(asset["file_path"])).exists())
            self.assertGreater(int(asset["size"]), 0)

    def test_legacy_csv_writer_still_writes_directly(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "legacy.csv"

            write_csv(path, [{"metric": "sales", "value": "100"}])

            self.assertTrue(path.exists())
            self.assertGreater(path.stat().st_size, 0)


class _ReportService(ReportService):
    def __init__(self) -> None:
        pass

    def build_meituan_daily_report(self, request):
        return ProcessingResult(
            module="anta_meituan_daily",
            output_rows=[{"metric": "sales", "value": "100"}],
            summary={"report_date": request.report_date},
            warnings=[],
        )


def _report_task(output_dir: Path) -> TaskRequest:
    return TaskRequest(
        task_id=2,
        task_type=TaskType.REPORT_GENERATE,
        created_by="admin",
        payload={
            "report_period": "daily",
            "brand_id": "anta_kids",
            "platform": "meituan",
            "channel": "instant_retail",
            "report_date": "20260725",
            "output_folder": str(output_dir),
        },
        created_time="2026-07-30T17:05:00+08:00",
    )


if __name__ == "__main__":
    unittest.main()
