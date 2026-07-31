from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from backend.repositories.interfaces import FoundationCheckRecord, FoundationRepository
from intranet_app.data_foundation import IngestionPlan, UploadMetadata, build_ingestion_plan


@dataclass(frozen=True)
class DataFoundationProcessRequest:
    import_batch_id: str
    metadata: UploadMetadata
    rows: list[dict[str, str]]
    known_store_ids: tuple[str, ...]
    known_product_codes: tuple[str, ...]
    original_file_name: str
    stored_file_path: Path
    file_sha256: str

    def __post_init__(self) -> None:
        if not isinstance(self.metadata, UploadMetadata):
            raise TypeError("metadata must be UploadMetadata")
        if not isinstance(self.rows, list):
            raise TypeError("rows must be list")
        for row in self.rows:
            if not isinstance(row, dict):
                raise TypeError("each row must be dict")
        if not isinstance(self.known_store_ids, tuple):
            raise TypeError("known_store_ids must be tuple")
        if not isinstance(self.known_product_codes, tuple):
            raise TypeError("known_product_codes must be tuple")
        for field_name, field_value in (
            ("import_batch_id", self.import_batch_id),
            ("original_file_name", self.original_file_name),
            ("file_sha256", self.file_sha256),
        ):
            if not isinstance(field_value, str) or not field_value.strip():
                raise ValueError(f"{field_name} must not be empty")
        if not isinstance(self.stored_file_path, Path):
            raise TypeError("stored_file_path must be pathlib.Path")


@dataclass(frozen=True)
class DataFoundationProcessResult:
    import_batch_id: str
    status: str
    imported: bool
    plan: IngestionPlan

    def __post_init__(self) -> None:
        if not isinstance(self.import_batch_id, str) or not self.import_batch_id.strip():
            raise ValueError("import_batch_id must not be empty")
        if not isinstance(self.status, str) or not self.status.strip():
            raise ValueError("status must not be empty")
        if not isinstance(self.imported, bool):
            raise TypeError("imported must be bool")
        if not isinstance(self.plan, IngestionPlan):
            raise TypeError("plan must be IngestionPlan")


class DataFoundationService:
    def __init__(self, foundation_repository: FoundationRepository) -> None:
        if not isinstance(foundation_repository, FoundationRepository):
            raise TypeError("foundation_repository must be FoundationRepository")
        self._foundation_repository = foundation_repository

    def process_rows(self, request: DataFoundationProcessRequest) -> DataFoundationProcessResult:
        if not isinstance(request, DataFoundationProcessRequest):
            raise TypeError("request must be DataFoundationProcessRequest")

        plan = build_ingestion_plan(
            request.metadata,
            request.rows,
            request.known_store_ids,
            request.known_product_codes,
        )
        status = _foundation_status(plan)
        self._foundation_repository.save_foundation_check(
            FoundationCheckRecord(
                import_batch_id=request.import_batch_id,
                metadata=request.metadata,
                original_file_name=request.original_file_name,
                stored_file_path=request.stored_file_path,
                file_sha256=request.file_sha256,
                recognized_file_type=plan.recognition.file_type,
                row_count=len(plan.normalized_rows),
                status=status,
                brand_match_score=plan.brand_match.total_score,
                validation_errors=plan.validation.errors,
                validation_warnings=plan.validation.warnings + plan.brand_match.warnings,
            )
        )
        imported = status == "ready_for_import"
        if imported:
            self._foundation_repository.save_foundation_rows(request.import_batch_id, plan)

        result = DataFoundationProcessResult(
            import_batch_id=request.import_batch_id,
            status=status,
            imported=imported,
            plan=plan,
        )
        assert isinstance(result, DataFoundationProcessResult)
        return result


def _foundation_status(plan: IngestionPlan) -> str:
    if not isinstance(plan, IngestionPlan):
        raise TypeError("plan must be IngestionPlan")
    if not plan.validation.passed:
        return "validation_failed"
    if plan.brand_match.decision == "auto_pass":
        return "ready_for_import"
    return plan.brand_match.decision
