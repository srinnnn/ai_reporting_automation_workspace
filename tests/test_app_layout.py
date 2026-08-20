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
    def test_workspace_overview_summary_uses_brand_scoped_metrics(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            (root / "materials").mkdir()
            app = IntranetApp(_config(root))
            app.storage = _EmptyStorage()
            user = UserRecord(1, "admin", "系统管理员", "管理员", PasswordHash("salt", "digest"))
            cases = {
                "ANTA": 2,
                "ECCO": 1,
                "BSH": 2,
            }

            for brand_key, active_priority_count in cases.items():
                with self.subTest(brand_key=brand_key):
                    workspace = app._workspace_overview_page(user, brand_key)
                    self.assertIn(
                        f"<article><span>已接分类</span><strong>{active_priority_count}</strong></article>",
                        workspace,
                    )
                    self.assertNotIn("隐藏能力", workspace)
                    self.assertNotIn("AI选品辅助", workspace)
                    self.assertNotIn("文案内容辅助", workspace)

    def test_dashboard_prioritizes_priority_entry_and_moves_project_stages_to_secondary_page(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            (root / "materials").mkdir()
            app = IntranetApp(_config(root))
            app.storage = _EmptyStorage()
            user = UserRecord(1, "admin", "系统管理员", "管理员", PasswordHash("salt", "digest"))

            dashboard = app._dashboard(user)

            self.assertIn("中台全局首页", dashboard)
            self.assertIn("品牌 Workspace 入口", dashboard)
            self.assertIn('href="/workspace?brand=ANTA"', dashboard)
            self.assertIn('href="/workspace?brand=ECCO"', dashboard)
            self.assertIn('href="/workspace?brand=BSH"', dashboard)
            self.assertNotIn("巡查", dashboard)
            self.assertNotIn("当前品牌工作台", dashboard)
            self.assertNotIn("安踏周报/月报", dashboard)
            self.assertNotIn("安踏即时零售", dashboard)
            self.assertNotIn("ECCO活动配置", dashboard)
            self.assertNotIn("博西短彩信数据处理", dashboard)
            self.assertNotIn("博世/西门子短彩信规划复核", dashboard)
            self.assertNotIn("AI选品辅助", dashboard)
            self.assertNotIn("文案内容辅助", dashboard)
            self.assertIn("最近处理记录", dashboard)
            self.assertIn('href="/data-foundation"', dashboard)
            self.assertIn('href="/automation-runs"', dashboard)
            self.assertIn('href="/archive-intake"', dashboard)
            self.assertNotIn('href="/p2-content-center"', dashboard)
            self.assertNotIn('href="/archive-index"', dashboard)
            self.assertNotIn('href="/data-dictionary"', dashboard)
            self.assertIn("parseDurationHours", dashboard)
            self.assertIn("formatTimeSaved", dashboard)

            workspace = app._workspace_overview_page(user, "ANTA")
            self.assertIn("ANTA 安踏", workspace)
            self.assertIn("P1", workspace)
            self.assertIn("数据提效", workspace)
            self.assertIn("P2", workspace)
            self.assertIn("内容提效", workspace)
            self.assertIn("P3", workspace)
            self.assertIn("配置提效", workspace)
            self.assertIn("P4", workspace)
            self.assertIn("复查", workspace)
            self.assertIn("<article><span>已接分类</span><strong>2</strong></article>", workspace)
            self.assertNotIn("隐藏能力", workspace)
            self.assertNotIn("安踏周报/月报", workspace)
            self.assertNotIn("安踏即时零售", workspace)

            p2_page = app._workspace_category_page(user, "ANTA", "P2")
            self.assertIn("P2 · 内容提效", p2_page)
            self.assertIn("当前品牌暂无接入能力", p2_page)
            self.assertNotIn("P2内容生产中心", p2_page)
            self.assertNotIn("AI选品辅助", p2_page)
            self.assertNotIn("文案内容辅助", p2_page)

            p1_page = app._workspace_category_page(user, "ANTA", "P1")
            self.assertIn("安踏周报/月报", p1_page)
            self.assertIn('href="/anta-reporting"', p1_page)
            self.assertNotIn("安踏即时零售", p1_page)

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
