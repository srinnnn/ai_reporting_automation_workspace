from __future__ import annotations

import logging
from dataclasses import dataclass

from .domain import Scenario


@dataclass(frozen=True)
class WorkspaceBrand:
    key: str
    label: str
    source_brands: tuple[str, ...]

    def __post_init__(self) -> None:
        for field_name, value in (("key", self.key), ("label", self.label)):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must be non-empty text")
        if not isinstance(self.source_brands, tuple) or not self.source_brands:
            raise ValueError("source_brands must be a non-empty tuple")
        for source_brand in self.source_brands:
            if not isinstance(source_brand, str) or not source_brand.strip():
                raise ValueError("source_brands must contain non-empty text")


PRIORITY_SECTIONS = (
    ("P1", "数据提效", "统一沉淀基础数据层，优先自动化日报、周报、月报和指标分析。"),
    ("P2", "内容提效", "围绕选品、策略、卖点、文案和视觉Brief做内容生产提效。"),
    ("P3", "配置提效", "用规则引擎和网页工具承接重复配置，并保留人工确认节点。"),
    ("P4", "复查", "沉淀规划复核、复盘和问题判断口径，成熟后逐步自动化。"),
)
WORKSPACE_BRANDS = (
    WorkspaceBrand("ANTA", "ANTA 安踏", ("安踏儿童", "安踏即时零售")),
    WorkspaceBrand("ECCO", "ECCO", ("ECCO",)),
    WorkspaceBrand("BSH", "BSH 博西", ("博西", "博世/西门子")),
)
MULTI_BRAND_SOURCE_BRAND = "多品牌"


def _workspace_brand_for_source_brand(source_brand: str) -> WorkspaceBrand | None:
    if not isinstance(source_brand, str) or not source_brand.strip():
        raise ValueError("source_brand must be non-empty text")
    if source_brand == MULTI_BRAND_SOURCE_BRAND:
        logging.info("source brand is not a workspace brand: %s", source_brand)
        return None
    for workspace_brand in WORKSPACE_BRANDS:
        if source_brand in workspace_brand.source_brands:
            assert isinstance(workspace_brand, WorkspaceBrand)
            return workspace_brand
    logging.info("workspace brand mapping unknown for source brand: %s", source_brand)
    return None


def _workspace_brand_options(scenarios: dict[str, Scenario]) -> tuple[WorkspaceBrand, ...]:
    if not isinstance(scenarios, dict):
        raise TypeError("scenarios must be dict")
    option_keys: list[str] = []
    for scenario in scenarios.values():
        if not isinstance(scenario, Scenario):
            raise TypeError("scenarios values must be Scenario")
        workspace_brand = _workspace_brand_for_source_brand(scenario.brand)
        if workspace_brand is not None and workspace_brand.key not in option_keys:
            option_keys.append(workspace_brand.key)
    options = tuple(workspace_brand for workspace_brand in WORKSPACE_BRANDS if workspace_brand.key in option_keys)
    assert all(isinstance(option, WorkspaceBrand) for option in options)
    return options


def _default_workspace_brand_key(scenarios: dict[str, Scenario]) -> str:
    options = _workspace_brand_options(scenarios)
    if not options:
        raise ValueError("at least one workspace brand option is required")
    result = options[0].key
    assert result
    return result


def _normalize_workspace_brand_key(raw_key: str, scenarios: dict[str, Scenario]) -> str:
    if raw_key is None:
        raise TypeError("raw_key must be str")
    if not isinstance(raw_key, str):
        raise TypeError("raw_key must be str")
    valid_keys = {option.key for option in _workspace_brand_options(scenarios)}
    if raw_key in valid_keys:
        assert raw_key
        return raw_key
    default_key = _default_workspace_brand_key(scenarios)
    logging.info("invalid workspace brand failed closed to default: %s -> %s", raw_key, default_key)
    assert default_key in valid_keys
    return default_key


def _workspace_brand_by_key(workspace_brand_key: str, scenarios: dict[str, Scenario]) -> WorkspaceBrand:
    if not isinstance(workspace_brand_key, str) or not workspace_brand_key.strip():
        raise ValueError("workspace_brand_key must be non-empty text")
    for option in _workspace_brand_options(scenarios):
        if option.key == workspace_brand_key:
            assert isinstance(option, WorkspaceBrand)
            return option
    raise ValueError("workspace_brand_key must be a valid workspace option")


def _workspace_scenario_keys_by_priority(scenarios: dict[str, Scenario], workspace_brand_key: str) -> dict[str, tuple[str, ...]]:
    workspace_brand = _workspace_brand_by_key(workspace_brand_key, scenarios)
    grouped: dict[str, list[str]] = {priority: [] for priority, _, _ in PRIORITY_SECTIONS}
    seen_keys: set[str] = set()
    for scenario_key, scenario in scenarios.items():
        if not isinstance(scenario_key, str) or not scenario_key.strip():
            raise ValueError("scenario keys must be non-empty text")
        if not isinstance(scenario, Scenario):
            raise TypeError("scenarios values must be Scenario")
        normalized_brand = _workspace_brand_for_source_brand(scenario.brand)
        if normalized_brand is None or normalized_brand.key != workspace_brand.key:
            continue
        if scenario.priority not in grouped:
            raise ValueError("scenario priority must be P1-P4")
        if scenario_key in seen_keys:
            raise ValueError("scenario keys must be unique across workspace priorities")
        grouped[scenario.priority].append(scenario_key)
        seen_keys.add(scenario_key)
    result = {priority: tuple(keys) for priority, keys in grouped.items()}
    assert set(result) == {priority for priority, _, _ in PRIORITY_SECTIONS}
    return result
