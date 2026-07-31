from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from backend.repositories.interfaces import FoundationRepository, ReportCreate, ReportRepository
from intranet_app.domain import ProcessingResult, ValidationError
from intranet_app.processors import anta_meituan_reporting


@dataclass(frozen=True)
class MeituanReportRequest:
    brand_id: str
    platform: str
    channel: str
    report_date: str

    def __post_init__(self) -> None:
        for field_name, field_value in (
            ("brand_id", self.brand_id),
            ("platform", self.platform),
            ("channel", self.channel),
            ("report_date", self.report_date),
        ):
            if not isinstance(field_value, str) or not field_value.strip():
                raise ValueError(f"{field_name} must not be empty")


@dataclass(frozen=True)
class MeituanWeeklyReportRequest:
    brand_id: str
    platform: str
    channel: str
    start_date: str
    end_date: str

    def __post_init__(self) -> None:
        for field_name, field_value in (
            ("brand_id", self.brand_id),
            ("platform", self.platform),
            ("channel", self.channel),
            ("start_date", self.start_date),
            ("end_date", self.end_date),
        ):
            if not isinstance(field_value, str) or not field_value.strip():
                raise ValueError(f"{field_name} must not be empty")


@dataclass(frozen=True)
class ReportSaveRequest:
    module: str
    title: str
    brand: str
    business_type: str
    created_by: str
    input_file: Path
    result_file: Path

    def __post_init__(self) -> None:
        for field_name, field_value in (
            ("module", self.module),
            ("title", self.title),
            ("brand", self.brand),
            ("business_type", self.business_type),
            ("created_by", self.created_by),
        ):
            if not isinstance(field_value, str) or not field_value.strip():
                raise ValueError(f"{field_name} must not be empty")
        if not isinstance(self.input_file, Path):
            raise TypeError("input_file must be pathlib.Path")
        if not isinstance(self.result_file, Path):
            raise TypeError("result_file must be pathlib.Path")


class ReportService:
    def __init__(
        self,
        foundation_repository: FoundationRepository,
        report_repository: ReportRepository | None = None,
    ) -> None:
        if not isinstance(foundation_repository, FoundationRepository):
            raise TypeError("foundation_repository must be FoundationRepository")
        if report_repository is not None and not isinstance(report_repository, ReportRepository):
            raise TypeError("report_repository must be ReportRepository")
        self._foundation_repository = foundation_repository
        self._report_repository = report_repository

    def build_meituan_daily_report(self, request: MeituanReportRequest) -> ProcessingResult:
        if not isinstance(request, MeituanReportRequest):
            raise TypeError("request must be MeituanReportRequest")
        sources = self._load_meituan_sources(request.brand_id, request.platform, request.channel)
        result = anta_meituan_reporting.build_meituan_daily_report(sources, request.report_date)
        assert isinstance(result, ProcessingResult)
        return result

    def build_meituan_weekly_report(self, request: MeituanWeeklyReportRequest) -> ProcessingResult:
        if not isinstance(request, MeituanWeeklyReportRequest):
            raise TypeError("request must be MeituanWeeklyReportRequest")
        sources = self._load_meituan_sources(request.brand_id, request.platform, request.channel)
        result = anta_meituan_reporting.build_meituan_weekly_report(sources, request.start_date, request.end_date)
        assert isinstance(result, ProcessingResult)
        return result

    def build_meituan_monthly_report(self) -> ProcessingResult:
        raise NotImplementedError("Meituan monthly report is not foundation-backed yet")

    def save_report_result(self, request: ReportSaveRequest, result: ProcessingResult) -> int:
        if self._report_repository is None:
            raise ValueError("report_repository is required to save report results")
        if not isinstance(request, ReportSaveRequest):
            raise TypeError("request must be ReportSaveRequest")
        if not isinstance(result, ProcessingResult):
            raise TypeError("result must be ProcessingResult")
        report_id = self._report_repository.save_report(
            ReportCreate(
                module=request.module,
                title=request.title,
                brand=request.brand,
                business_type=request.business_type,
                created_by=request.created_by,
                input_file=request.input_file,
                result_file=request.result_file,
                summary=result.summary,
                warnings=result.warnings,
            )
        )
        assert report_id > 0
        return report_id

    def _load_meituan_sources(
        self,
        brand_id: str,
        platform: str,
        channel: str,
    ) -> anta_meituan_reporting.MeituanReportSources:
        sources = anta_meituan_reporting.MeituanReportSources(
            product_rows=self._query_required_rows(brand_id, platform, channel, "product_order"),
            finance_rows=self._foundation_repository.query_foundation_rows(brand_id, platform, channel, "store_finance"),
            traffic_rows=self._foundation_repository.query_foundation_rows(brand_id, platform, channel, "store_traffic"),
            review_rows=self._foundation_repository.query_foundation_rows(brand_id, platform, channel, "service_review"),
        )
        assert isinstance(sources, anta_meituan_reporting.MeituanReportSources)
        return sources

    def _query_required_rows(
        self,
        brand_id: str,
        platform: str,
        channel: str,
        file_type: str,
    ) -> list[dict[str, str]]:
        rows = self._foundation_repository.query_foundation_rows(brand_id, platform, channel, file_type)
        if not rows:
            raise ValidationError("基础数据层缺少商品/订单数据，不能生成正式报表。")
        return rows
