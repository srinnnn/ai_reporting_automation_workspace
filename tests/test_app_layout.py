from __future__ import annotations

import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from intranet_app.app import CompletedFeedbackItem, GROUP_PROJECT_TREE_ITEMS, IntranetApp, _parse_duration_hours
from intranet_app.auth import PasswordHash
from intranet_app.config import AppConfig
from intranet_app.domain import ProcessingResult
from intranet_app.storage import UserRecord


class AppLayoutTests(unittest.TestCase):
    def test_dashboard_prioritizes_priority_entry_and_moves_project_stages_to_secondary_page(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            (root / "materials").mkdir()
            app = IntranetApp(_config(root))
            app.storage = _EmptyStorage()
            user = UserRecord(1, "admin", "系统管理员", "管理员", PasswordHash("salt", "digest"))

            dashboard = app._dashboard(user)
            stages = app._project_stages_page(user, "", "")

            self.assertLess(dashboard.index("P1-P4 分级入口"), dashboard.index("开发覆盖总览"))
            self.assertLess(dashboard.index("开发覆盖总览"), dashboard.index("已开发反馈汇总"))
            self.assertLess(dashboard.index("已开发反馈汇总"), dashboard.index("最近处理记录"))
            self.assertIn("全组项目开发与覆盖总览", dashboard)
            self.assertNotIn("项目分支</span>", dashboard)
            self.assertNotIn("展示层级</span>", dashboard)
            self.assertIn("数据提效", dashboard)
            self.assertIn("内容提效", dashboard)
            self.assertIn("配置提效", dashboard)
            self.assertIn("巡查", dashboard)
            self.assertIn("项目总数", dashboard)
            self.assertIn("已经开发总数", dashboard)
            self.assertIn("待开发总数", dashboard)
            self.assertIn('class="priority-stat-total"', dashboard)
            self.assertIn('class="priority-stat-developed"', dashboard)
            self.assertIn('class="priority-stat-pending"', dashboard)
            self.assertIn("38个可提效项目明细", dashboard)
            self.assertIn("<strong>38</strong>", dashboard)
            self.assertIn("已提效项目", dashboard)
            self.assertIn('class="efficiency-mapping-panel compact-efficiency-panel"', dashboard)
            self.assertNotIn("已提效任务</span>", dashboard)
            self.assertNotIn("已提效品牌项", dashboard)
            self.assertNotIn('class="efficiency-mapping-summary compact-summary"', dashboard)
            self.assertIn("brand-logo-chip", dashboard)
            self.assertIn("日报（日常销售报数）", dashboard)
            self.assertIn("安踏", dashboard)
            self.assertIn("短彩信数据追踪", dashboard)
            self.assertIn('href="/efficiency-mapping"', dashboard)
            self.assertNotIn('action="/efficiency-mapping/save"', dashboard)
            self.assertNotIn("待提效项", dashboard)
            self.assertIn("已提效", dashboard)
            self.assertNotIn("<small>· P1</small>", dashboard)
            self.assertIn('href="/work-item-planning"', dashboard)
            self.assertNotIn('class="project-map-grid"', dashboard)
            self.assertNotIn('class="project-map-lane priority-border-p1"', dashboard)
            self.assertNotIn('href="#project-detail-1"', dashboard)
            self.assertNotIn('class="project-modal"', dashboard)
            self.assertNotIn("具体工作内容", dashboard)
            self.assertIn('class="feedback-summary-panel merged-feedback-summary"', dashboard)
            self.assertIn('class="data-table dashboard-stage-table"', dashboard)
            self.assertIn("优先级", dashboard)
            self.assertIn("已开发品牌", dashboard)
            self.assertIn("原耗时数据", dashboard)
            self.assertIn("现在耗时数据", dashboard)
            self.assertIn("提效时间", dashboard)
            self.assertIn("业务反馈", dashboard)
            self.assertNotIn('class="completed-feedback-card"', dashboard)
            self.assertNotIn('name="return_to" value="/"', dashboard)
            self.assertEqual(dashboard.count('href="/data-foundation"'), 1)
            self.assertEqual(dashboard.count('href="/automation-runs"'), 1)
            self.assertEqual(dashboard.count('href="/archive-intake"'), 1)
            self.assertEqual(dashboard.count('href="/work-item-planning"'), 1)
            self.assertNotIn('href="/p2-content-center"', dashboard)
            self.assertNotIn('href="/archive-index"', dashboard)
            self.assertNotIn('href="/data-dictionary"', dashboard)
            self.assertEqual(dashboard.count('href="/project-stages"'), 1)
            self.assertNotIn("<h2>项目开发阶段</h2>", dashboard)
            self.assertIn("已开发完整业务反馈", dashboard)
            self.assertNotIn("这里只展示已提效映射生成的反馈卡", dashboard)
            self.assertNotIn('name="project" value="P1-日报（日常销售报数）-安踏"', dashboard)
            self.assertNotIn('name="project" value="P1-周报（周数据整合）-安踏"', dashboard)
            self.assertNotIn('name="project" value="P3-上下架处理-安踏"', dashboard)
            self.assertNotIn('name="project" value="P1-短彩信数据追踪-CK"', dashboard)
            self.assertNotIn("博西短彩信数据处理", dashboard)
            self.assertNotIn("安踏即时零售", dashboard)
            self.assertIn("上下架处理", dashboard)
            self.assertIn("短彩信数据追踪", dashboard)
            self.assertNotIn('name="project" value="P1-短彩信数据处理-博西"', dashboard)
            self.assertNotIn('name="project" value="P3-即时零售-安踏"', dashboard)
            self.assertIn("parseDurationHours", dashboard)
            self.assertIn("formatTimeSaved", dashboard)
            self.assertIn("<span>CK</span>", dashboard)
            self.assertIn("<span>Armani</span>", dashboard)
            self.assertIn("<span>Tommy</span>", dashboard)
            self.assertIn("<span>安踏</span>", dashboard)
            self.assertIn("<h1>项目开发阶段</h1>", stages)
            self.assertNotIn("博西短彩信数据处理", stages)
            self.assertNotIn("安踏即时零售", stages)
            self.assertNotIn('id="project-feedback-1"', stages)
            self.assertNotIn('class="project-stage-list"', stages)
            self.assertNotIn('class="ledger-summary stage-summary project-stage-summary"', stages)
            self.assertNotIn('class="data-table project-stage-table"', stages)
            self.assertIn('name="business_feedback"', stages)
            self.assertIn('name="iteration_need"', stages)
            self.assertIn('name="current_processing_time"', stages)
            self.assertIn('action="/project-stages/feedback"', stages)
            self.assertIn("已开发完整业务反馈", stages)
            self.assertIn("已开发品牌", stages)
            self.assertIn('class="completed-feedback-card"', stages)
            self.assertIn('name="return_to" value="/project-stages"', stages)
            self.assertIn('name="project" value="P3-上下架处理-安踏"', stages)
            self.assertIn("data-time-saved-output", stages)
            self.assertIn('class="efficiency-source-input"', stages)

            p2_page = app._priority_page(user, "P2")
            self.assertIn("P2内容生产中心", p2_page)
            self.assertIn('href="/p2-content-center"', p2_page)
            self.assertIn("AI选品辅助", p2_page)
            self.assertIn("文案内容辅助", p2_page)

            work_items = app._work_item_planning_page(user)
            self.assertIn("<h1>38个可提效项目明细</h1>", work_items)
            self.assertIn('href="/efficiency-mapping"', work_items)
            self.assertIn("优先开发", work_items)
            self.assertIn('class="project-map-grid"', work_items)
            self.assertIn('class="project-map-lane priority-border-p1"', work_items)
            self.assertIn('href="#project-detail-1"', work_items)
            self.assertIn('class="project-modal"', work_items)
            self.assertIn("具体工作内容", work_items)
            self.assertIn("A/B · 可提效", work_items)
            self.assertIn("C · 暂不提效", work_items)
            self.assertIn('class="project-map-card priority-card-p4 is-not-efficiency-fit"', work_items)
            self.assertIn("可替代类型", work_items)
            self.assertIn("无法 AI 提效，保留人工协同", work_items)

            mapping_page = app._efficiency_mapping_page(user, "")
            self.assertIn("高耗时任务映射台账", mapping_page)
            self.assertIn("手动增加品牌", mapping_page)
            self.assertIn("全部待提效和排期", mapping_page)
            self.assertIn('class="efficiency-priority-section priority-border-p1"', mapping_page)
            self.assertIn('class="efficiency-brand-entry is-improved"', mapping_page)
            self.assertIn('class="brand-entry-chip brand-logo-chip"', mapping_page)
            self.assertIn("替代/提效理由", mapping_page)
            self.assertIn("规则明确、频率高、模板稳定", mapping_page)
            self.assertIn('action="/efficiency-mapping/save"', mapping_page)
            self.assertIn('action="/efficiency-mapping/add-brand"', mapping_page)
            self.assertIn('name="is_improved"', mapping_page)
            self.assertIn('name="not_improved_reason"', mapping_page)
            self.assertIn('name="schedule_plan"', mapping_page)
            self.assertIn("待提效", mapping_page)
            self.assertNotIn("涉及业务方", mapping_page)

    def test_development_roadmap_page_is_beginner_friendly_and_complete(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            (root / "materials").mkdir()
            app = IntranetApp(_config(root))
            app.storage = _EmptyStorage()
            user = UserRecord(1, "admin", "系统管理员", "管理员", PasswordHash("salt", "digest"))

            page = app._development_roadmap_page(user)

            self.assertIn("数据处理 + AI智能Brief详细开发排期", page)
            self.assertIn("2026-07-27 至 2026-10-02", page)
            self.assertIn("按模板交资料", page)
            self.assertIn("你需要做", page)
            self.assertIn("我负责开发", page)
            self.assertIn("通过标准", page)
            self.assertIn("美团订单/商品原始数据", page)
            self.assertEqual(page.count('class="roadmap-week"'), 10)
            self.assertEqual(page.count('class="roadmap-day-row"'), 50)

    def test_copy_content_page_links_to_downloadable_template(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            (root / "materials").mkdir()
            app = IntranetApp(_config(root))
            app.storage = _EmptyStorage()
            user = UserRecord(1, "admin", "系统管理员", "管理员", PasswordHash("salt", "digest"))

            page = app._scenario_page(user, "copy_content", "")

            self.assertIn('href="/scenario/copy_content/template"', page)
            self.assertIn("copy_content_template_anta_kids_example.xlsx", page)

    def test_copy_content_result_page_shows_generated_copy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            (root / "materials").mkdir()
            app = IntranetApp(_config(root))
            app.storage = _EmptyStorage()
            user = UserRecord(1, "admin", "系统管理员", "管理员", PasswordHash("salt", "digest"))
            result = ProcessingResult(
                module="copy_content",
                output_rows=[
                    {
                        "商品名称": "UFO8男大童跑步系列秋季跑鞋",
                        "AI标题建议": "安踏儿童UFO8秋季跑鞋",
                        "AI正文建议": "面向男大童及其家长的商品短文案。",
                        "合规状态": "通过",
                    }
                ],
                summary={"处理内容数": "1"},
                warnings=[],
            )

            page = app._result_page(user, 5, result)

            self.assertIn("文案生成结果", page)
            self.assertIn("安踏儿童UFO8秋季跑鞋", page)
            self.assertIn("面向男大童及其家长的商品短文案。", page)
            self.assertIn("E 列是 AI 标题，F 列是 AI 正文", page)

    def test_completed_feedback_card_escapes_feedback_key_with_ampersand(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            (root / "materials").mkdir()
            app = IntranetApp(_config(root))
            item = CompletedFeedbackItem(
                priority="P3",
                project="安踏上下架&黑名单",
                brand="安踏",
                feedback_key="P3-安踏上下架&黑名单-安踏",
                legacy_project="P3-安踏上下架&黑名单-安踏",
                manual_time_project="安踏即时零售",
            )

            card = app._completed_feedback_card(item, {}, {})

            self.assertIn('value="P3-安踏上下架&amp;黑名单-安踏"', card)
            self.assertIn("安踏上下架&amp;黑名单", card)


class DashboardTreeCalculationTests(unittest.TestCase):
    def test_group_project_tree_has_p1_to_p4_and_expected_total(self) -> None:
        priorities = {item.priority for item in GROUP_PROJECT_TREE_ITEMS}
        total_hours = sum((item.original_hours for item in GROUP_PROJECT_TREE_ITEMS), Decimal("0"))

        self.assertEqual(priorities, {"P1", "P2", "P3", "P4"})
        self.assertEqual(len(GROUP_PROJECT_TREE_ITEMS), 44)
        self.assertEqual(total_hours, Decimal("11341"))

    def test_platform_architecture_groups_channel_brands(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            (root / "materials").mkdir()
            app = IntranetApp(_config(root))
            groups = app._project_platform_groups()

        platforms = {group.platform for group in groups}

        self.assertIn("CRM", platforms)
        self.assertIn("京东", platforms)
        self.assertIn("小程序", platforms)
        self.assertIn("企微/社群", platforms)
        self.assertIn("飞猪", platforms)
        self.assertIn("经销", platforms)

        crm_group = next(group for group in groups if group.platform == "CRM")
        crm_brands = {brand.brand for brand in crm_group.brands}
        developed_crm_brands = {brand.brand for brand in crm_group.brands if brand.is_developed}
        mini_program_group = next(group for group in groups if group.platform == "小程序")
        wecom_group = next(group for group in groups if group.platform == "企微/社群")

        self.assertIn("Nes", crm_brands)
        self.assertIn("Vans", crm_brands)
        self.assertIn("CROCS", crm_brands)
        self.assertIn("CK", developed_crm_brands)
        self.assertIn("Armani", developed_crm_brands)
        self.assertIn("Tommy", developed_crm_brands)
        self.assertIn("Nes", developed_crm_brands)
        self.assertIn("安踏", {brand.brand for brand in mini_program_group.brands})
        self.assertIn("安踏", {brand.brand for brand in wecom_group.brands})

    def test_saved_not_improved_state_overrides_default_improved_rule(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            (root / "materials").mkdir()
            app = IntranetApp(_config(root))
            app.storage = _StorageWithEfficiencyOverride()

            items = app._high_efficiency_mapping_items()
            monthly_report = next(item for item in items if item.task_name == "月报（月报表整合/规划项）")
            anta_brand = next(brand for brand in monthly_report.brands if brand.brand_name == "安踏")

            self.assertFalse(anta_brand.is_improved)

    def test_parse_duration_hours_supports_minutes_and_hours(self) -> None:
        self.assertEqual(_parse_duration_hours("40分钟/次"), Decimal("40") / Decimal("60"))
        self.assertEqual(_parse_duration_hours("6小时/月"), Decimal("6"))
        self.assertEqual(_parse_duration_hours("2400分钟"), Decimal("40"))
        self.assertIsNone(_parse_duration_hours(""))
        self.assertIsNone(_parse_duration_hours("待填写"))

    def test_time_saved_formats_hours(self) -> None:
        self.assertEqual(IntranetApp._format_time_saved(Decimal("40"), "40分钟"), "39.33小时")
        self.assertEqual(IntranetApp._format_time_saved(Decimal("40"), "6小时"), "34小时")
        self.assertEqual(IntranetApp._format_time_saved(Decimal("40"), ""), "待计算")
        self.assertEqual(IntranetApp._format_time_saved(Decimal("1"), "2小时"), "未提效")

    def test_p2_development_stats_are_not_counted_as_developed_yet(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            (root / "materials").mkdir()
            app = IntranetApp(_config(root))

            stats = app._priority_development_stats("P2")

            self.assertEqual(stats.total_count, 7)
            self.assertEqual(stats.developed_count, 0)
            self.assertEqual(stats.pending_count, 7)


class _EmptyStorage:
    def list_jobs(self) -> list[object]:
        return []

    def list_project_feedback(self) -> dict[str, object]:
        return {}

    def list_efficiency_mapping_notes(self) -> dict[tuple[str, str], object]:
        return {}


class _StorageWithEfficiencyOverride(_EmptyStorage):
    def list_efficiency_mapping_notes(self) -> dict[tuple[str, str], object]:
        from intranet_app.storage import EfficiencyMappingRecord

        return {
            ("月报（月报表整合/规划项）", "安踏"): EfficiencyMappingRecord(
                task_name="月报（月报表整合/规划项）",
                brand_name="安踏",
                not_improved_reason="后台已取消提效",
                schedule_plan="待重新确认",
                is_improved=False,
                is_manual_brand=False,
                updated_by="admin",
                updated_at="2026-07-28 12:00:00",
            )
        }


def _config(root: Path) -> AppConfig:
    if not isinstance(root, Path):
        raise TypeError("root must be pathlib.Path")
    return AppConfig(
        host="127.0.0.1",
        port=8765,
        secret_key="test-secret",
        database_path=root / "runtime" / "intranet.sqlite3",
        upload_dir=root / "runtime" / "uploads",
        result_dir=root / "runtime" / "results",
        template_root=root / "materials",
        default_admin_password="admin123",
    )


if __name__ == "__main__":
    unittest.main()
