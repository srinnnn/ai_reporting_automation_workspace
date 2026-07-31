from __future__ import annotations

from dataclasses import dataclass
import unittest

from backend.adapters.report_task_adapter import (
    ANTA_MEITUAN_DAILY_BRAND_ID,
    ANTA_MEITUAN_DAILY_BRAND_NAME,
    FOUNDATION_ONLY_SOURCE_POLICY,
    build_daily_report_task_payload,
)


@dataclass(frozen=True)
class TestUser:
    username: str


class ReportTaskAdapterTests(unittest.TestCase):
    def test_builds_daily_report_payload(self) -> None:
        payload = build_daily_report_task_payload("20260725", _user())

        self.assertEqual(payload["task_name"], "\u5b89\u8e0f\u513f\u7ae5\u7f8e\u56e2\u65e5\u62a5-20260725")
        self.assertEqual(payload["brand_id"], ANTA_MEITUAN_DAILY_BRAND_ID)
        self.assertEqual(payload["brand_name"], ANTA_MEITUAN_DAILY_BRAND_NAME)
        self.assertEqual(payload["platform"], "meituan")
        self.assertEqual(payload["channel"], "instant_retail")
        self.assertEqual(payload["report_type"], "daily")
        self.assertEqual(payload["report_period"], "daily")
        self.assertEqual(payload["report_date"], "20260725")
        self.assertEqual(payload["source_policy"], FOUNDATION_ONLY_SOURCE_POLICY)
        self.assertEqual(payload["created_by"], "admin")

    def test_converts_hyphenated_date_to_compact_date(self) -> None:
        payload = build_daily_report_task_payload("2026-07-25", _user())

        self.assertEqual(payload["date"], "20260725")
        self.assertEqual(payload["date_window"], "20260725")

    def test_missing_user_information_is_rejected(self) -> None:
        with self.assertRaisesRegex(TypeError, "current_user"):
            build_daily_report_task_payload("20260725", None)


def _user() -> TestUser:
    return TestUser(username="admin")


if __name__ == "__main__":
    unittest.main()
