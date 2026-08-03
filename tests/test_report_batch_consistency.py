from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from backend.repositories.interfaces import FoundationRepository
from scripts.report_consistency_runner import run_batch_consistency


class ReportBatchConsistencyTests(unittest.TestCase):
    def test_batch_runner_passes_for_date_range(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            report = run_batch_consistency("20260725", "20260726", _FoundationRepository(), Path(temp_dir))

            self.assertTrue(report.passed)
            self.assertEqual(len(report.rows), 2)
            self.assertTrue(report.output_path.exists())
            self.assertEqual([row.date for row in report.rows], ["20260725", "20260726"])
            self.assertTrue(all(row.legacy_rows == row.task_rows for row in report.rows))
            self.assertTrue(all(row.amount_delta == "0.00" for row in report.rows))

    def test_batch_runner_writes_acceptance_report_csv(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            report = run_batch_consistency("20260725", "20260725", _FoundationRepository(), Path(temp_dir))
            with report.output_path.open("r", encoding="utf-8-sig", newline="") as handle:
                rows = list(csv.DictReader(handle))

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["\u65e5\u671f"], "20260725")
        self.assertEqual(rows[0]["legacy_status"], "success")
        self.assertEqual(rows[0]["task_status"], "success")
        self.assertEqual(rows[0]["result"], "PASS")
        self.assertIn("amount_delta", rows[0])
        self.assertIn("field_diff", rows[0])

    def test_single_day_failure_does_not_block_later_dates(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            report = run_batch_consistency("20260725", "20260727", _FailingOneDayFoundationRepository("20260726"), Path(temp_dir))

        self.assertEqual(len(report.rows), 3)
        self.assertEqual([row.result for row in report.rows], ["PASS", "FAIL", "PASS"])
        self.assertIn("ValidationError", report.rows[1].message)
        self.assertFalse(report.passed)

    def test_invalid_date_range_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaises(ValueError):
                run_batch_consistency("20260727", "20260725", _FoundationRepository(), Path(temp_dir))


class _FoundationRepository(FoundationRepository):
    def save_foundation_check(self, record):
        raise NotImplementedError

    def save_foundation_rows(self, import_batch_id: str, plan):
        raise NotImplementedError

    def query_foundation_rows(self, brand_id: str, platform: str, channel: str, file_type: str) -> list[dict[str, str]]:
        if file_type == "product_order":
            return self._product_rows()
        if file_type == "store_finance":
            return self._finance_rows()
        if file_type == "store_traffic":
            return self._traffic_rows()
        if file_type == "service_review":
            return []
        return []

    def _product_rows(self) -> list[dict[str, str]]:
        return [
            _product_row("20260725", "order-1", "store-xian", "UFO shoes", "2", "200"),
            _product_row("20260726", "order-2", "store-hangzhou", "Swim suit", "1", "100"),
            _product_row("20260727", "order-3", "store-xian", "UFO shoes", "1", "100"),
        ]

    def _finance_rows(self) -> list[dict[str, str]]:
        return [
            _finance_row("20260725", "store-1", "store-xian", "200", "1"),
            _finance_row("20260726", "store-2", "store-hangzhou", "100", "1"),
            _finance_row("20260727", "store-1", "store-xian", "100", "1"),
        ]

    def _traffic_rows(self) -> list[dict[str, str]]:
        return [
            _traffic_row("20260725", "store-1", "store-xian"),
            _traffic_row("20260726", "store-2", "store-hangzhou"),
            _traffic_row("20260727", "store-1", "store-xian"),
        ]


class _FailingOneDayFoundationRepository(_FoundationRepository):
    def __init__(self, failing_date: str) -> None:
        self.failing_date = failing_date

    def _product_rows(self) -> list[dict[str, str]]:
        return [row for row in super()._product_rows() if row["\u65e5\u671f"] != self.failing_date]

    def _finance_rows(self) -> list[dict[str, str]]:
        return [row for row in super()._finance_rows() if row["\u5f00\u59cb\u65f6\u95f4"] != self.failing_date]

    def _traffic_rows(self) -> list[dict[str, str]]:
        return [row for row in super()._traffic_rows() if row["\u5f00\u59cb\u65f6\u95f4"] != self.failing_date]


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


if __name__ == "__main__":
    unittest.main()
