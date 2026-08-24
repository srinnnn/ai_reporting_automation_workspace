from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DemoScheduleFixture:
    key: str
    name: str
    brand_key: str
    status: str
    milestone: str
    risk: str

    def __post_init__(self) -> None:
        for field_name, value in (
            ("key", self.key),
            ("name", self.name),
            ("brand_key", self.brand_key),
            ("status", self.status),
            ("milestone", self.milestone),
            ("risk", self.risk),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must be non-empty text")


DEMO_SCHEDULE: tuple[DemoScheduleFixture, ...] = (
    DemoScheduleFixture(
        key="v3-runtime",
        name="V3 Runtime Migration",
        brand_key="PLATFORM",
        status="DEMO",
        milestone="React + FastAPI",
        risk="LOW",
    ),
    DemoScheduleFixture(
        key="visual-baseline",
        name="Runtime Visual Baseline",
        brand_key="PLATFORM",
        status="DEMO",
        milestone="Playwright visual regression",
        risk="MEDIUM",
    ),
)
