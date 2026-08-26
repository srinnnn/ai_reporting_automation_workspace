from __future__ import annotations

import logging
from dataclasses import dataclass

from backend.repositories.interfaces import FeedbackRepository
from backend.schemas.platform import FeedbackSummary, ProjectSummary
from intranet_app.storage import ProjectFeedbackRecord

# Exact compatibility keys proven by the legacy feedback dashboard and its
# efficiency mapping. Brand/category/status still come from ProjectSummary.
LEGACY_FEEDBACK_PROJECT_KEYS: dict[str, str] = {
    "P1-短彩信数据处理-博西": "bosch_sms",
    "P1-短彩信数据追踪-博西": "bosch_sms",
    "P3-即时零售-安踏": "anta_retail",
    "P3-上下架处理-安踏": "anta_retail",
    "P3-活动机制配置-ECCO": "ecco_activity_config",
}


@dataclass(frozen=True)
class FeedbackFilters:
    brand: str | None = None
    category: str | None = None
    project: str | None = None
    status: str | None = None

    def __post_init__(self) -> None:
        for field_name, value in (
            ("brand", self.brand),
            ("category", self.category),
            ("project", self.project),
            ("status", self.status),
        ):
            if value is not None and (not isinstance(value, str) or not value.strip()):
                raise ValueError(f"{field_name} must be non-empty text when provided")
        if self.category is not None and self.category.strip().upper() not in {"P1", "P2", "P3", "P4"}:
            raise ValueError("category must be P1-P4")


@dataclass(frozen=True)
class FeedbackService:
    repository: FeedbackRepository
    projects: tuple[ProjectSummary, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.repository, FeedbackRepository):
            raise TypeError("repository must implement FeedbackRepository")
        if not isinstance(self.projects, tuple):
            raise TypeError("projects must be tuple")
        if not all(isinstance(project, ProjectSummary) for project in self.projects):
            raise TypeError("projects must contain ProjectSummary")

    def list_feedback(self, filters: FeedbackFilters | None = None) -> tuple[FeedbackSummary, ...]:
        if filters is not None and not isinstance(filters, FeedbackFilters):
            raise TypeError("filters must be FeedbackFilters or None")
        active_filters = filters or FeedbackFilters()
        records = tuple(_map_feedback_record(record, self.projects) for record in self.repository.list_feedback())
        result = tuple(record for record in records if _matches_filters(record, active_filters))
        assert all(isinstance(record, FeedbackSummary) for record in result)
        logging.info(
            "feedback query completed: total=%s mapped=%s returned=%s",
            len(records),
            sum(1 for record in records if record.status != "UNMAPPED"),
            len(result),
        )
        return result


def _map_feedback_record(record: ProjectFeedbackRecord, projects: tuple[ProjectSummary, ...]) -> FeedbackSummary:
    if not isinstance(record, ProjectFeedbackRecord):
        raise TypeError("record must be ProjectFeedbackRecord")
    if not isinstance(projects, tuple) or not all(isinstance(project, ProjectSummary) for project in projects):
        raise TypeError("projects must contain ProjectSummary")
    projects_by_key = {project.key: project for project in projects}
    projects_by_name = {project.name: project for project in projects}
    mapped_project = projects_by_key.get(record.project) or projects_by_name.get(record.project)
    if mapped_project is None:
        legacy_project_key = LEGACY_FEEDBACK_PROJECT_KEYS.get(record.project)
        mapped_project = projects_by_key.get(legacy_project_key) if legacy_project_key is not None else None
    if mapped_project is None:
        logging.info("feedback project remains unmapped: project=%s", record.project)
    result = FeedbackSummary(
        project=record.project,
        mapped_project_key=mapped_project.key if mapped_project is not None else None,
        mapped_project_name=mapped_project.name if mapped_project is not None else None,
        brand_key=mapped_project.brand_key if mapped_project is not None else None,
        category_key=mapped_project.category_key if mapped_project is not None else None,
        status=mapped_project.status if mapped_project is not None else "UNMAPPED",
        original_manual_time=record.original_manual_time,
        current_processing_time=record.current_processing_time,
        business_feedback=record.business_feedback,
        iteration_need=record.iteration_need,
        updated_by=record.updated_by,
        updated_at=record.updated_at,
    )
    assert result.project == record.project
    return result


def _matches_filters(record: FeedbackSummary, filters: FeedbackFilters) -> bool:
    if not isinstance(record, FeedbackSummary):
        raise TypeError("record must be FeedbackSummary")
    if not isinstance(filters, FeedbackFilters):
        raise TypeError("filters must be FeedbackFilters")
    if filters.brand is not None and record.brand_key != filters.brand.strip().upper():
        return False
    if filters.category is not None and record.category_key != filters.category.strip().upper():
        return False
    if filters.status is not None and record.status != filters.status.strip().upper():
        return False
    if filters.project is not None:
        project_filter = filters.project.strip()
        if project_filter not in {record.project, record.mapped_project_key, record.mapped_project_name}:
            return False
    return True
