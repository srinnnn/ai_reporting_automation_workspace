from __future__ import annotations

from intranet_app.storage import AppStorage, JobRecord

from ..interfaces import ReportCreate, ReportRepository


class SQLiteReportRepository(ReportRepository):
    def __init__(self, storage: AppStorage) -> None:
        if not isinstance(storage, AppStorage):
            raise TypeError("storage must be AppStorage")
        self._storage = storage

    def save_report(self, request: ReportCreate) -> int:
        if not isinstance(request, ReportCreate):
            raise TypeError("request must be ReportCreate")
        report_id = self._storage.save_job(
            module=request.module,
            title=request.title,
            brand=request.brand,
            business_type=request.business_type,
            created_by=request.created_by,
            input_file=request.input_file,
            result_file=request.result_file,
            summary=request.summary,
            warnings=request.warnings,
        )
        assert report_id > 0
        return report_id

    def get_report(self, report_id: int) -> JobRecord | None:
        if not isinstance(report_id, int) or report_id <= 0:
            raise ValueError("report_id must be positive int")
        return self._storage.get_job(report_id)
