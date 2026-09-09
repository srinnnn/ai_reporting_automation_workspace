from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from backend.fixtures.demo_platform import DEMO_SCHEDULE
from backend.schemas.platform import BrandSummary, CapabilitySummary, CategorySummary, DashboardSummary, EmptyModule, ProjectSummary, ScheduleItem
from intranet_app.scenarios import build_scenarios
from intranet_app.workspace_metadata import PRIORITY_SECTIONS, _workspace_brand_options, _workspace_scenario_keys_by_priority


PRIVATE_DATA_LOCAL_CENTER_KEY = "private_data_local_center"
PRIVATE_DATA_LOCAL_CENTER_INTEGRATION_KEY = "private-data-local-center"
PRIVATE_DATA_LOCAL_CENTER_ENTRY_PATH = "/integrations/private-data-local-center/#/collection/requests/new"
PRIVATE_DATA_LOCAL_CENTER_CAPABILITY = CapabilitySummary(
    key=PRIVATE_DATA_LOCAL_CENTER_KEY,
    name="私域数据采集中心",
    brand_key="ANTA",
    category_key="P1",
    status="CONFIGURED",
)


@dataclass(frozen=True)
class PlatformService:
    template_root: Path
    demo_mode: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.template_root, Path):
            raise TypeError("template_root must be pathlib.Path")
        if not isinstance(self.demo_mode, bool):
            raise TypeError("demo_mode must be bool")

    def dashboard(self) -> DashboardSummary:
        brands = self.brands()
        projects = self.projects()
        kpis = {
            "brand_count": len(brands),
            "connected_project_count": len(projects),
            "runtime_entry": "8785",
            "demo_mode": "true" if self.demo_mode else "false",
        }
        result = DashboardSummary(brands=brands, projects=projects, kpis=kpis)
        assert isinstance(result, DashboardSummary)
        return result

    def brands(self) -> tuple[BrandSummary, ...]:
        scenarios = build_scenarios(self.template_root)
        result = tuple(
            self._brand(option.key, option.label, "Brand Workspace", _workspace_scenario_keys_by_priority(scenarios, option.key), scenarios)
            for option in _workspace_brand_options(scenarios)
        )
        assert result
        return result

    def brand(self, brand_key: str) -> BrandSummary | None:
        if not isinstance(brand_key, str) or not brand_key.strip():
            raise ValueError("brand_key must not be empty")
        normalized = brand_key.strip().upper()
        for brand in self.brands():
            if brand.key == normalized:
                return brand
        return None

    def projects(self) -> tuple[ProjectSummary, ...]:
        result = tuple(
            ProjectSummary(
                key=capability.key,
                name=capability.name,
                brand_key=brand.key,
                category_key=category.key,
                status=capability.status,
                integration_key=(
                    PRIVATE_DATA_LOCAL_CENTER_INTEGRATION_KEY
                    if capability.key == PRIVATE_DATA_LOCAL_CENTER_KEY
                    else None
                ),
                entry_path=(
                    PRIVATE_DATA_LOCAL_CENTER_ENTRY_PATH
                    if capability.key == PRIVATE_DATA_LOCAL_CENTER_KEY
                    else None
                ),
            )
            for brand in self.brands()
            for category in brand.categories
            for capability in category.capabilities
        )
        assert result
        return result

    def project(self, project_key: str) -> ProjectSummary | None:
        if not isinstance(project_key, str) or not project_key.strip():
            raise ValueError("project_key must not be empty")
        normalized = project_key.strip()
        for project in self.projects():
            if project.key == normalized:
                return project
        return None

    def schedule(self) -> tuple[ScheduleItem, ...]:
        if not self.demo_mode:
            return ()
        result = tuple(
            ScheduleItem(
                key=item.key,
                name=item.name,
                brand_key=item.brand_key,
                status=item.status,
                milestone=item.milestone,
                risk=item.risk,
            )
            for item in DEMO_SCHEDULE
        )
        assert result
        return result

    def module(self, route: str, title: str) -> EmptyModule:
        if not route.startswith("/"):
            raise ValueError("route must start with slash")
        if not title.strip():
            raise ValueError("title must not be empty")
        result = EmptyModule(route=route, title=title, status="NOT_CONNECTED", message="暂无真实业务数据，已保留正式页面入口。")
        assert isinstance(result, EmptyModule)
        return result

    @staticmethod
    def _brand(
        key: str,
        name: str,
        tagline: str,
        scenario_keys_by_priority: dict[str, tuple[str, ...]],
        scenarios: dict[str, object],
    ) -> BrandSummary:
        categories = tuple(
            _category(key, category_key, category_name, scenario_keys_by_priority[category_key], scenarios)
            for category_key, category_name, _ in PRIORITY_SECTIONS
        )
        if key == PRIVATE_DATA_LOCAL_CENTER_CAPABILITY.brand_key:
            categories = tuple(_with_private_data_local_center(category) for category in categories)
        result = BrandSummary(
            key=key,
            name=name,
            tagline=tagline,
            active_category_count=sum(1 for category in categories if category.capability_count > 0),
            categories=categories,
        )
        assert isinstance(result, BrandSummary)
        return result


def _category(
    brand_key: str,
    category_key: str,
    category_name: str,
    scenario_keys: tuple[str, ...],
    scenarios: object,
) -> CategorySummary:
    if not isinstance(scenarios, dict):
        raise TypeError("scenarios must be dict")
    capabilities = tuple(
        CapabilitySummary(
            key=scenario_key,
            name=scenarios[scenario_key].name,
            brand_key=brand_key,
            category_key=category_key,
            status="CONNECTED",
        )
        for scenario_key in scenario_keys
    )
    result = CategorySummary(
        key=category_key,
        name=category_name,
        capability_count=len(capabilities),
        status="CONNECTED" if capabilities else "NOT_CONNECTED",
        capabilities=capabilities,
    )
    assert isinstance(result, CategorySummary)
    return result


def _with_private_data_local_center(category: CategorySummary) -> CategorySummary:
    if category.key != PRIVATE_DATA_LOCAL_CENTER_CAPABILITY.category_key:
        return category
    if any(item.key == PRIVATE_DATA_LOCAL_CENTER_KEY for item in category.capabilities):
        return category
    capabilities = (*category.capabilities, PRIVATE_DATA_LOCAL_CENTER_CAPABILITY)
    return CategorySummary(
        key=category.key,
        name=category.name,
        capability_count=len(capabilities),
        status="CONNECTED",
        capabilities=capabilities,
    )
