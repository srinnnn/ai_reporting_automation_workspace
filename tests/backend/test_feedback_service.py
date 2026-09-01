from __future__ import annotations

import unittest
from dataclasses import dataclass

from backend.repositories.interfaces import FeedbackRepository
from backend.schemas.platform import ProjectSummary
from backend.services.feedback_service import FeedbackFilters, FeedbackService
from intranet_app.storage import ProjectFeedbackRecord


@dataclass(frozen=True)
class StubFeedbackRepository(FeedbackRepository):
    records: tuple[ProjectFeedbackRecord, ...]

    def list_feedback(self) -> tuple[ProjectFeedbackRecord, ...]:
        return self.records


class FeedbackServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        projects = (
            ProjectSummary(key="anta_reporting", name="安踏周报/月报", brand_key="ANTA", category_key="P1", status="CONNECTED"),
            ProjectSummary(key="anta_retail", name="安踏即时零售", brand_key="ANTA", category_key="P3", status="CONNECTED"),
            ProjectSummary(key="ecco_activity_config", name="ECCO活动配置", brand_key="ECCO", category_key="P3", status="CONNECTED"),
            ProjectSummary(key="bosch_sms", name="博西短彩信数据处理", brand_key="BSH", category_key="P1", status="CONNECTED"),
        )
        records = (
            _feedback("安踏周报/月报"),
            _feedback("P3-即时零售-安踏"),
            _feedback("P3-活动机制配置-ECCO"),
            _feedback("P1-短彩信数据追踪-博西"),
            _feedback("P1-短彩信数据处理-CK"),
        )
        self.service = FeedbackService(repository=StubFeedbackRepository(records), projects=projects)

    def test_maps_exact_names_and_legacy_compatibility_keys(self) -> None:
        records = self.service.list_feedback()
        by_source = {record.project: record for record in records}

        self.assertEqual(len(records), 5)
        self.assertEqual(by_source["安踏周报/月报"].mapped_project_key, "anta_reporting")
        self.assertEqual(by_source["P3-即时零售-安踏"].brand_key, "ANTA")
        self.assertEqual(by_source["P3-活动机制配置-ECCO"].brand_key, "ECCO")
        self.assertEqual(by_source["P1-短彩信数据追踪-博西"].brand_key, "BSH")
        self.assertEqual(by_source["P1-短彩信数据处理-CK"].status, "UNMAPPED")
        self.assertIsNone(by_source["P1-短彩信数据处理-CK"].brand_key)

    def test_filters_by_brand_without_leaking_unmapped_records(self) -> None:
        anta = self.service.list_feedback(FeedbackFilters(brand="anta"))
        ecco = self.service.list_feedback(FeedbackFilters(brand="ECCO"))
        bsh = self.service.list_feedback(FeedbackFilters(brand="BSH"))

        self.assertEqual({record.project for record in anta}, {"安踏周报/月报", "P3-即时零售-安踏"})
        self.assertEqual([record.project for record in ecco], ["P3-活动机制配置-ECCO"])
        self.assertEqual([record.project for record in bsh], ["P1-短彩信数据追踪-博西"])

    def test_filters_by_category_project_and_status(self) -> None:
        p1 = self.service.list_feedback(FeedbackFilters(category="P1"))
        project = self.service.list_feedback(FeedbackFilters(project="anta_retail"))
        unmapped = self.service.list_feedback(FeedbackFilters(status="UNMAPPED"))

        self.assertEqual({record.project for record in p1}, {"安踏周报/月报", "P1-短彩信数据追踪-博西"})
        self.assertEqual([record.project for record in project], ["P3-即时零售-安踏"])
        self.assertEqual([record.project for record in unmapped], ["P1-短彩信数据处理-CK"])

    def test_empty_repository_returns_empty_result(self) -> None:
        service = FeedbackService(repository=StubFeedbackRepository(()), projects=self.service.projects)

        self.assertEqual(service.list_feedback(), ())

    def test_invalid_category_fails_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "P1-P4"):
            FeedbackFilters(category="P5")


def _feedback(project: str) -> ProjectFeedbackRecord:
    return ProjectFeedbackRecord(
        project=project,
        original_manual_time="2小时",
        current_processing_time="1小时",
        business_feedback="真实反馈",
        iteration_need="真实迭代需求",
        updated_by="tester",
        updated_at="2026-08-26 10:00:00",
    )


if __name__ == "__main__":
    unittest.main()
