from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from backend.repositories.interfaces import FoundationRepository, ReportCreate, ReportRepository
from backend.services.ai_service import AIService
from intranet_app.content_pipeline import P2ContentRequest, build_p2_content_pack
from intranet_app.domain import ProcessingResult, ValidationError


PRODUCT_ORDER_FILE_TYPE = "product_order"
SERVICE_REVIEW_FILE_TYPE = "service_review"


@dataclass(frozen=True)
class AIContentSaveRequest:
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


class AIContentService:
    def __init__(
        self,
        foundation_repository: FoundationRepository,
        ai_service: AIService,
        report_repository: ReportRepository | None = None,
    ) -> None:
        if not isinstance(foundation_repository, FoundationRepository):
            raise TypeError("foundation_repository must be FoundationRepository")
        if not isinstance(ai_service, AIService):
            raise TypeError("ai_service must be AIService")
        if report_repository is not None and not isinstance(report_repository, ReportRepository):
            raise TypeError("report_repository must be ReportRepository")
        self._foundation_repository = foundation_repository
        self._ai_service = ai_service
        self._report_repository = report_repository

    def build_content_pack(self, request: P2ContentRequest) -> ProcessingResult:
        if not isinstance(request, P2ContentRequest):
            raise TypeError("request must be P2ContentRequest")
        product_rows = self._foundation_repository.query_foundation_rows(
            request.brand_id,
            request.platform,
            request.channel,
            PRODUCT_ORDER_FILE_TYPE,
        )
        review_rows = self._foundation_repository.query_foundation_rows(
            request.brand_id,
            request.platform,
            request.channel,
            SERVICE_REVIEW_FILE_TYPE,
        )
        result = build_p2_content_pack(request, product_rows, review_rows, self._ai_service.generate_text)
        self._validate_content_result(result)
        logging.info("AI content pack built: brand=%s task_type=%s", request.brand_id, request.task_type)
        assert isinstance(result, ProcessingResult)
        return result

    def save_content_result(self, request: AIContentSaveRequest, result: ProcessingResult) -> int:
        if self._report_repository is None:
            raise ValueError("report_repository is required to save AI content results")
        if not isinstance(request, AIContentSaveRequest):
            raise TypeError("request must be AIContentSaveRequest")
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

    def _validate_content_result(self, result: ProcessingResult) -> None:
        if not isinstance(result, ProcessingResult):
            raise TypeError("result must be ProcessingResult")
        if not result.output_rows:
            raise ValidationError("AI content result has no output rows")
        for row in result.output_rows:
            if not isinstance(row, dict):
                raise TypeError("each output row must be dict")
            ai_fields = [key for key in row.keys() if "AI" in str(key)]
            if not ai_fields:
                raise ValidationError("AI content result is missing generated content fields")
            if all(not str(row.get(key, "")).strip() for key in ai_fields):
                raise ValidationError("AI content result generated fields are empty")
