from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class CategorySummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    key: str = Field(pattern=r"^P[1-4]$")
    name: str
    capability_count: int = Field(ge=0)
    status: str
    capabilities: tuple["CapabilitySummary", ...] = ()


class CapabilitySummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    key: str
    name: str
    brand_key: str
    category_key: str = Field(pattern=r"^P[1-4]$")
    status: str


class BrandSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    key: str
    name: str
    tagline: str
    active_category_count: int = Field(ge=0)
    categories: tuple[CategorySummary, ...]


class ProjectSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    key: str
    name: str
    brand_key: str
    category_key: str = Field(pattern=r"^P[1-4]$")
    status: str


class FeedbackSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    project: str
    mapped_project_key: str | None = None
    mapped_project_name: str | None = None
    brand_key: str | None = None
    category_key: str | None = Field(default=None, pattern=r"^P[1-4]$")
    status: str
    original_manual_time: str
    current_processing_time: str
    business_feedback: str
    iteration_need: str
    updated_by: str
    updated_at: str


class DashboardSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    brands: tuple[BrandSummary, ...]
    projects: tuple[ProjectSummary, ...]
    kpis: dict[str, int | str]


class ScheduleItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    key: str
    name: str
    brand_key: str
    status: str
    milestone: str
    risk: str


class EmptyModule(BaseModel):
    model_config = ConfigDict(frozen=True)

    route: str
    title: str
    status: str
    message: str
