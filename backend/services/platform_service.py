from __future__ import annotations

from dataclasses import dataclass

from backend.schemas.platform import BrandSummary, CategorySummary, DashboardSummary, EmptyModule, ProjectSummary, ScheduleItem


P_CATEGORIES: tuple[tuple[str, str], ...] = (
    ("P1", "数据提效"),
    ("P2", "内容提效"),
    ("P3", "配置提效"),
    ("P4", "复查"),
)


@dataclass(frozen=True)
class PlatformService:
    demo_mode: bool = False

    def __post_init__(self) -> None:
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
        if not self.demo_mode:
            return ()
        result = (
            self._brand("ANTA", "ANTA 安踏", "Demo brand workspace", {"P1": 1, "P3": 1}),
            self._brand("ECCO", "ECCO", "Demo brand workspace", {"P3": 1}),
            self._brand("BSH", "BSH 博西家电", "Demo brand workspace", {"P1": 1, "P4": 1}),
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
        if not self.demo_mode:
            return ()
        result = (
            ProjectSummary(key="anta-reporting", name="安踏周报/月报", brand_key="ANTA", category_key="P1", status="DEMO"),
            ProjectSummary(key="anta-retail", name="安踏即时零售", brand_key="ANTA", category_key="P3", status="DEMO"),
            ProjectSummary(key="ecco-activity-config", name="ECCO活动配置", brand_key="ECCO", category_key="P3", status="DEMO"),
            ProjectSummary(key="bsh-sms-data", name="博西短彩信数据处理", brand_key="BSH", category_key="P1", status="DEMO"),
            ProjectSummary(key="bsh-sms-review", name="博世/西门子短彩信规划复核", brand_key="BSH", category_key="P4", status="DEMO"),
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
        result = (
            ScheduleItem(key="v3-runtime", name="V3 Runtime Migration", brand_key="PLATFORM", status="DEMO", milestone="React + FastAPI", risk="LOW"),
            ScheduleItem(key="visual-baseline", name="Runtime Visual Baseline", brand_key="PLATFORM", status="DEMO", milestone="Playwright screenshot", risk="MEDIUM"),
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
    def _brand(key: str, name: str, tagline: str, capability_counts: dict[str, int]) -> BrandSummary:
        categories = tuple(
            CategorySummary(
                key=category_key,
                name=category_name,
                capability_count=capability_counts.get(category_key, 0),
                status="DEMO" if capability_counts.get(category_key, 0) > 0 else "NOT_CONNECTED",
            )
            for category_key, category_name in P_CATEGORIES
        )
        result = BrandSummary(
            key=key,
            name=name,
            tagline=tagline,
            active_category_count=sum(1 for category in categories if category.capability_count > 0),
            categories=categories,
        )
        assert isinstance(result, BrandSummary)
        return result
