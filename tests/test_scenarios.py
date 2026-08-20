from __future__ import annotations

import unittest
from pathlib import Path

from intranet_app.app import IntranetApp
from intranet_app.processors import ai_selection, anta_reporting, bosch_sms, copy_content
from intranet_app.scenarios import (
    ANTA_RETAIL_KEY,
    BOSCH_SMS_REVIEW_KEY,
    ECCO_ACTIVITY_CONFIG_KEY,
    build_scenarios,
)


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


def _template_root() -> Path:
    return Path("ai_report_config_materials")


def _scenario_href(scenario_key: str) -> str:
    app = object.__new__(IntranetApp)
    return app._scenario_href(scenario_key)


if __name__ == "__main__":
    unittest.main()
