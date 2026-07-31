from __future__ import annotations

from typing import Any

from intranet_app.storage import AppStorage

from ..interfaces import FoundationCheckRecord, FoundationRepository


class SQLiteFoundationRepository(FoundationRepository):
    def __init__(self, storage: AppStorage) -> None:
        if not isinstance(storage, AppStorage):
            raise TypeError("storage must be AppStorage")
        self._storage = storage

    def save_foundation_check(self, record: FoundationCheckRecord) -> None:
        if not isinstance(record, FoundationCheckRecord):
            raise TypeError("record must be FoundationCheckRecord")
        self._storage.save_foundation_check(
            import_batch_id=record.import_batch_id,
            metadata=record.metadata,
            original_file_name=record.original_file_name,
            stored_file_path=record.stored_file_path,
            file_sha256=record.file_sha256,
            recognized_file_type=record.recognized_file_type,
            row_count=record.row_count,
            status=record.status,
            brand_match_score=record.brand_match_score,
            validation_errors=record.validation_errors,
            validation_warnings=record.validation_warnings,
        )

    def save_foundation_rows(self, import_batch_id: str, plan: Any) -> None:
        if not isinstance(import_batch_id, str) or not import_batch_id.strip():
            raise ValueError("import_batch_id must not be empty")
        self._storage.save_foundation_fact_rows(import_batch_id.strip(), plan)

    def query_foundation_rows(
        self,
        brand_id: str,
        platform: str,
        channel: str,
        file_type: str,
    ) -> list[dict[str, str]]:
        for field_name, field_value in (
            ("brand_id", brand_id),
            ("platform", platform),
            ("channel", channel),
            ("file_type", file_type),
        ):
            if not isinstance(field_value, str) or not field_value.strip():
                raise ValueError(f"{field_name} must not be empty")
        rows = self._storage.load_meituan_foundation_rows(
            brand_id.strip(),
            platform.strip(),
            channel.strip(),
            file_type.strip(),
        )
        assert isinstance(rows, list)
        return rows
