from __future__ import annotations

import unittest
from pathlib import Path
from types import SimpleNamespace

from intranet_app.app import (
    IntranetApp,
    PRIORITY_SECTIONS,
    RequestContext,
    _normalize_workspace_brand_key,
    _workspace_brand_for_source_brand,
    _workspace_brand_options,
    _workspace_scenario_keys_by_priority,
)
from intranet_app.auth import PasswordHash
from intranet_app.processors import ai_selection, anta_reporting, bosch_sms, copy_content
from intranet_app.scenarios import (
    ANTA_RETAIL_KEY,
    BOSCH_SMS_REVIEW_KEY,
    ECCO_ACTIVITY_CONFIG_KEY,
    build_scenarios,
)
from intranet_app.storage import UserRecord


class ScenarioRegistryTests(unittest.TestCase):
    def test_existing_scenarios_keep_contract_fields(self) -> None:
        scenarios = build_scenarios(_template_root())

        expected = {
            bosch_sms.MODULE_KEY: ("博西短彩信数据处理", "P1", "博西", "数据处理"),
            anta_reporting.MODULE_KEY: ("安踏周报/月报", "P1", "安踏儿童", "数据处理"),
            ANTA_RETAIL_KEY: ("安踏即时零售", "P3", "安踏即时零售", "配置自动化"),
            ai_selection.MODULE_KEY: ("AI选品辅助", "P2", "多品牌", "AI选品"),
            copy_content.MODULE_KEY: ("文案内容辅助", "P2", "多品牌", "文案内容"),
        }

        for key, (name, priority, brand, business_type) in expected.items():
            scenario = scenarios[key]
            self.assertEqual(scenario.key, key)
            self.assertEqual(scenario.name, name)
            self.assertEqual(scenario.priority, priority)
            self.assertEqual(scenario.brand, brand)
            self.assertEqual(scenario.business_type, business_type)

    def test_ecco_activity_config_scenario_is_registered_and_routable(self) -> None:
        scenarios = build_scenarios(_template_root())
        scenario = scenarios[ECCO_ACTIVITY_CONFIG_KEY]

        self.assertEqual(scenario.name, "ECCO活动配置")
        self.assertEqual(scenario.priority, "P3")
        self.assertEqual(scenario.brand, "ECCO")
        self.assertEqual(scenario.business_type, "配置自动化")
        self.assertIn("参活清单", scenario.required_fields[0])
        self.assertEqual(_scenario_href(ECCO_ACTIVITY_CONFIG_KEY), "/scenario/ecco_activity_config")

    def test_bosch_siemens_sms_review_scenario_is_registered_and_routable(self) -> None:
        scenarios = build_scenarios(_template_root())
        scenario = scenarios[BOSCH_SMS_REVIEW_KEY]

        self.assertEqual(scenario.name, "博世/西门子短彩信规划复核")
        self.assertEqual(scenario.priority, "P4")
        self.assertEqual(scenario.brand, "博世/西门子")
        self.assertEqual(scenario.business_type, "规划复核")
        self.assertIn("短彩信发送规划表", scenario.required_fields[0])
        self.assertEqual(_scenario_href(BOSCH_SMS_REVIEW_KEY), "/scenario/bosch_sms_review")

    def test_scenario_keys_are_unique(self) -> None:
        scenarios = build_scenarios(_template_root())

        self.assertEqual(len(scenarios), len(set(scenarios)))

    def test_scenario_priorities_are_valid(self) -> None:
        scenarios = build_scenarios(_template_root())

        self.assertEqual({scenario.priority for scenario in scenarios.values()}, {"P1", "P2", "P3", "P4"})

    def test_scenario_baseline_sync_does_not_add_workspace_logic(self) -> None:
        scenarios = build_scenarios(_template_root())

        for scenario in scenarios.values():
            self.assertFalse(hasattr(scenario, "workspace_brand"))
        self.assertNotIn("workspace_brand", Path("intranet_app/scenarios.py").read_text(encoding="utf-8"))
        self.assertNotIn("brand selector", Path("intranet_app/scenarios.py").read_text(encoding="utf-8").lower())

    def test_workspace_brand_normalization_maps_anta_source_brands(self) -> None:
        self.assertEqual(_workspace_brand_for_source_brand("安踏儿童").key, "ANTA")
        self.assertEqual(_workspace_brand_for_source_brand("安踏即时零售").key, "ANTA")

    def test_workspace_brand_normalization_maps_ecco_and_bsh_source_brands(self) -> None:
        self.assertEqual(_workspace_brand_for_source_brand("ECCO").key, "ECCO")
        self.assertEqual(_workspace_brand_for_source_brand("博西").key, "BSH")
        self.assertEqual(_workspace_brand_for_source_brand("博世/西门子").key, "BSH")

    def test_multi_brand_is_not_workspace_selector_option(self) -> None:
        scenarios = build_scenarios(_template_root())
        options = _workspace_brand_options(scenarios)

        self.assertEqual([option.key for option in options], ["ANTA", "ECCO", "BSH"])
        self.assertEqual([option.label for option in options], ["ANTA 安踏", "ECCO", "BSH 博西"])
        self.assertNotIn("多品牌", {option.label for option in options})
        self.assertIsNone(_workspace_brand_for_source_brand("多品牌"))

    def test_anta_workspace_filter_includes_only_anta_capabilities(self) -> None:
        scenarios = build_scenarios(_template_root())
        grouped = _workspace_scenario_keys_by_priority(scenarios, "ANTA")
        workspace_keys = {key for keys in grouped.values() for key in keys}

        self.assertEqual(workspace_keys, {anta_reporting.MODULE_KEY, ANTA_RETAIL_KEY})
        self.assertNotIn(ECCO_ACTIVITY_CONFIG_KEY, workspace_keys)
        self.assertNotIn(BOSCH_SMS_REVIEW_KEY, workspace_keys)

    def test_anta_workspace_uses_scenario_priority_without_duplication(self) -> None:
        scenarios = build_scenarios(_template_root())
        grouped = _workspace_scenario_keys_by_priority(scenarios, "ANTA")

        self.assertEqual(grouped["P1"], (anta_reporting.MODULE_KEY,))
        self.assertEqual(grouped["P3"], (ANTA_RETAIL_KEY,))
        self.assertEqual(grouped["P2"], ())
        self.assertEqual(grouped["P4"], ())
        all_grouped_keys = [key for keys in grouped.values() for key in keys]
        self.assertEqual(len(all_grouped_keys), len(set(all_grouped_keys)))

    def test_ecco_workspace_uses_scenario_priority_without_duplication(self) -> None:
        scenarios = build_scenarios(_template_root())
        grouped = _workspace_scenario_keys_by_priority(scenarios, "ECCO")

        self.assertEqual(grouped["P1"], ())
        self.assertEqual(grouped["P2"], ())
        self.assertEqual(grouped["P3"], (ECCO_ACTIVITY_CONFIG_KEY,))
        self.assertEqual(grouped["P4"], ())
        all_grouped_keys = [key for keys in grouped.values() for key in keys]
        self.assertEqual(len(all_grouped_keys), len(set(all_grouped_keys)))

    def test_bsh_workspace_uses_scenario_priority_without_duplication(self) -> None:
        scenarios = build_scenarios(_template_root())
        grouped = _workspace_scenario_keys_by_priority(scenarios, "BSH")

        self.assertEqual(grouped["P1"], (bosch_sms.MODULE_KEY,))
        self.assertEqual(grouped["P2"], ())
        self.assertEqual(grouped["P3"], ())
        self.assertEqual(grouped["P4"], (BOSCH_SMS_REVIEW_KEY,))
        all_grouped_keys = [key for keys in grouped.values() for key in keys]
        self.assertEqual(len(all_grouped_keys), len(set(all_grouped_keys)))

    def test_workspace_coverage_distinguishes_visible_and_intentionally_hidden(self) -> None:
        scenarios = build_scenarios(_template_root())
        visible = {
            anta_reporting.MODULE_KEY,
            ANTA_RETAIL_KEY,
            ECCO_ACTIVITY_CONFIG_KEY,
            bosch_sms.MODULE_KEY,
            BOSCH_SMS_REVIEW_KEY,
        }
        intentionally_hidden = {
            ai_selection.MODULE_KEY: "BUSINESS_NOT_READY",
            copy_content.MODULE_KEY: "WORKSPACE_COVERAGE_UNKNOWN",
        }
        grouped_keys = {
            key
            for workspace_key in ("ANTA", "ECCO", "BSH")
            for keys in _workspace_scenario_keys_by_priority(scenarios, workspace_key).values()
            for key in keys
        }

        self.assertEqual(grouped_keys, visible)
        self.assertEqual(set(scenarios) - grouped_keys, set(intentionally_hidden))
        for key, reason in intentionally_hidden.items():
            self.assertIn(reason, {"BUSINESS_NOT_READY", "WORKSPACE_COVERAGE_UNKNOWN"})
            self.assertIsNone(_workspace_brand_for_source_brand(scenarios[key].brand))

    def test_anta_reporting_keeps_existing_route_from_workspace(self) -> None:
        app = _workspace_app()
        dashboard = app._dashboard(_user(), "ANTA")

        self.assertEqual(app._scenario_href(anta_reporting.MODULE_KEY), "/anta-reporting")
        self.assertIn('href="/anta-reporting"', dashboard)
        self.assertIn("安踏周报/月报", dashboard)

    def test_bsh_capabilities_keep_existing_routes_from_workspace(self) -> None:
        app = _workspace_app()
        dashboard = app._dashboard(_user(), "BSH")

        self.assertEqual(app._scenario_href(bosch_sms.MODULE_KEY), "/scenario/bosch_sms")
        self.assertEqual(app._scenario_href(BOSCH_SMS_REVIEW_KEY), "/scenario/bosch_sms_review")
        self.assertIn('href="/scenario/bosch_sms"', dashboard)
        self.assertIn('href="/scenario/bosch_sms_review"', dashboard)

    def test_invalid_workspace_brand_fails_closed_to_valid_brand_without_leakage(self) -> None:
        app = _workspace_app()
        dashboard = app._dashboard(_user(), "UNKNOWN")

        self.assertEqual(_normalize_workspace_brand_key("UNKNOWN", app.scenarios), "ANTA")
        self.assertIn("ANTA 安踏", dashboard)
        self.assertIn("安踏周报/月报", dashboard)
        self.assertIn("安踏即时零售", dashboard)
        self.assertNotIn("ECCO活动配置", dashboard)
        self.assertNotIn("博世/西门子短彩信规划复核", dashboard)

    def test_workspace_ui_uses_review_language_for_p4(self) -> None:
        app = _workspace_app()
        dashboard = app._dashboard(_user(), "ANTA")
        p4_page = app._priority_page(_user(), "P4", "ANTA")

        self.assertIn("P4 · 复查", dashboard)
        self.assertIn("P4 · 复查", p4_page)
        self.assertNotIn("巡查", dashboard)
        self.assertNotIn("巡查", p4_page)

    def test_priority_route_uses_workspace_brand_query_on_handle_get(self) -> None:
        app = _workspace_app()
        sent: dict[str, object] = {}
        app._context = lambda handler: RequestContext(_user(), "token")  # type: ignore[method-assign]
        app._send_html = lambda handler, content, status=200: sent.update({"content": content, "status": status})  # type: ignore[method-assign]

        app.handle_get(SimpleNamespace(path="/priority/P1?brand=ANTA"))

        page = str(sent["content"])
        self.assertEqual(sent["status"], 200)
        self.assertIn("ANTA 安踏", page)
        self.assertIn("安踏周报/月报", page)
        self.assertIn('href="/anta-reporting"', page)
        self.assertNotIn("ECCO活动配置", page)
        self.assertNotIn("博世/西门子短彩信规划复核", page)

    def test_bsh_priority_routes_use_workspace_brand_query_on_handle_get(self) -> None:
        app = _workspace_app()
        sent: dict[str, object] = {}
        app._context = lambda handler: RequestContext(_user(), "token")  # type: ignore[method-assign]
        app._send_html = lambda handler, content, status=200: sent.update({"content": content, "status": status})  # type: ignore[method-assign]

        app.handle_get(SimpleNamespace(path="/priority/P1?brand=BSH"))
        p1_page = str(sent["content"])
        self.assertEqual(sent["status"], 200)
        self.assertIn("BSH 博西", p1_page)
        self.assertIn("博西短彩信数据处理", p1_page)
        self.assertIn('href="/scenario/bosch_sms"', p1_page)
        self.assertNotIn("博世/西门子短彩信规划复核", p1_page)

        sent.clear()
        app.handle_get(SimpleNamespace(path="/priority/P4?brand=BSH"))
        p4_page = str(sent["content"])
        self.assertEqual(sent["status"], 200)
        self.assertIn("BSH 博西", p4_page)
        self.assertIn("博世/西门子短彩信规划复核", p4_page)
        self.assertIn('href="/scenario/bosch_sms_review"', p4_page)
        self.assertNotIn("博西短彩信数据处理", p4_page)

    def test_workspace_pages_isolate_capability_cards_by_brand(self) -> None:
        app = _workspace_app()
        pages = {
            "ANTA": app._dashboard(_user(), "ANTA"),
            "ECCO": app._dashboard(_user(), "ECCO"),
            "BSH": app._dashboard(_user(), "BSH"),
        }
        visible_by_workspace = {
            "ANTA": {"安踏周报/月报", "安踏即时零售"},
            "ECCO": {"ECCO活动配置"},
            "BSH": {"博西短彩信数据处理", "博世/西门子短彩信规划复核"},
        }
        hidden_everywhere = {"AI选品辅助", "文案内容辅助"}

        for workspace_key, page in pages.items():
            for capability in visible_by_workspace[workspace_key]:
                self.assertIn(capability, page)
            other_capabilities = set().union(*visible_by_workspace.values()) - visible_by_workspace[workspace_key]
            for capability in other_capabilities | hidden_everywhere:
                self.assertNotIn(capability, page)

    def test_workspace_selector_uses_only_workspace_keys(self) -> None:
        app = _workspace_app()
        dashboard = app._dashboard(_user(), "BSH")

        self.assertIn('<option value="ANTA">ANTA 安踏</option>', dashboard)
        self.assertIn('<option value="ECCO">ECCO</option>', dashboard)
        self.assertIn('<option value="BSH" selected>BSH 博西</option>', dashboard)
        self.assertNotIn('<option value="多品牌"', dashboard)
        self.assertNotIn('<option value="博西"', dashboard)
        self.assertNotIn('<option value="博世/西门子"', dashboard)

    def test_priority_category_contract_keeps_bsh_capabilities_in_expected_p_bucket(self) -> None:
        scenarios = build_scenarios(_template_root())
        grouped = _workspace_scenario_keys_by_priority(scenarios, "BSH")

        self.assertEqual(
            {priority: title for priority, title, _ in PRIORITY_SECTIONS},
            {"P1": "数据提效", "P2": "内容提效", "P3": "配置提效", "P4": "复查"},
        )
        self.assertEqual(scenarios[bosch_sms.MODULE_KEY].priority, "P1")
        self.assertEqual(scenarios[BOSCH_SMS_REVIEW_KEY].priority, "P4")
        self.assertEqual(grouped["P1"], (bosch_sms.MODULE_KEY,))
        self.assertEqual(grouped["P4"], (BOSCH_SMS_REVIEW_KEY,))
        self.assertNotIn(bosch_sms.MODULE_KEY, grouped["P4"])
        self.assertNotIn(BOSCH_SMS_REVIEW_KEY, grouped["P1"])


def _template_root() -> Path:
    return Path("ai_report_config_materials")


def _scenario_href(scenario_key: str) -> str:
    app = object.__new__(IntranetApp)
    return app._scenario_href(scenario_key)


def _workspace_app() -> IntranetApp:
    app = object.__new__(IntranetApp)
    app.scenarios = build_scenarios(_template_root())
    app.storage = _EmptyStorage()
    return app


def _user() -> UserRecord:
    return UserRecord(1, "admin", "系统管理员", "管理员", PasswordHash("salt", "digest"))


class _EmptyStorage:
    def list_jobs(self) -> list[object]:
        return []


if __name__ == "__main__":
    unittest.main()
