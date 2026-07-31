from __future__ import annotations

import unittest

from backend.services.ai_content_service import AIContentService
from backend.services.data_foundation_service import DataFoundationProcessResult, DataFoundationService
from backend.services.report_service import ReportService
from backend.workers.contracts import TaskRequest, TaskType, WorkerTaskStatus
from backend.workers.executors import BaseTaskExecutor
from backend.workers.executors.ai_content_executor import AIContentExecutor
from backend.workers.executors.data_import_executor import DataImportExecutor
from backend.workers.executors.report_executor import ReportExecutor
from intranet_app.data_foundation import UploadMetadata, build_ingestion_plan
from intranet_app.domain import ProcessingResult, ValidationError


class ExecutorAdapterTests(unittest.TestCase):
    def test_executor_creation_and_import_compatibility(self) -> None:
        data_executor = DataImportExecutor(_DataFoundationService())
        report_executor = ReportExecutor(_ReportService())
        ai_executor = AIContentExecutor(_AIContentService())

        self.assertIsInstance(data_executor, BaseTaskExecutor)
        self.assertIsInstance(report_executor, BaseTaskExecutor)
        self.assertIsInstance(ai_executor, BaseTaskExecutor)

    def test_data_import_executor_runs_mock_service(self) -> None:
        service = _DataFoundationService()
        executor = DataImportExecutor(service)

        result = executor.execute(_data_import_task())

        self.assertEqual(result.status, WorkerTaskStatus.SUCCESS)
        self.assertEqual(result.result["import_batch_id"], "batch-1")
        self.assertTrue(result.result["imported"])
        self.assertIsNotNone(service.last_request)

    def test_report_executor_runs_mock_service(self) -> None:
        service = _ReportService()
        executor = ReportExecutor(service)

        result = executor.execute(_report_task())

        self.assertEqual(result.status, WorkerTaskStatus.SUCCESS)
        self.assertEqual(result.result["module"], "anta_meituan_daily")
        self.assertEqual(result.result["output_row_count"], 1)
        self.assertEqual(service.last_daily_date, "20260725")

    def test_ai_content_executor_runs_mock_service(self) -> None:
        service = _AIContentService()
        executor = AIContentExecutor(service)

        result = executor.execute(_ai_content_task())

        self.assertEqual(result.status, WorkerTaskStatus.SUCCESS)
        self.assertEqual(result.result["module"], "p2_content_center")
        self.assertEqual(service.last_task_type, "social_copy")

    def test_service_exception_returns_failed_task_result(self) -> None:
        executor = ReportExecutor(_FailingReportService())

        result = executor.execute(_report_task())

        self.assertEqual(result.status, WorkerTaskStatus.FAILED)
        self.assertIn("foundation data missing", result.error)


class _DataFoundationService(DataFoundationService):
    def __init__(self) -> None:
        self.last_request = None

    def process_rows(self, request):
        self.last_request = request
        plan = build_ingestion_plan(request.metadata, request.rows, request.known_store_ids, request.known_product_codes)
        return DataFoundationProcessResult(
            import_batch_id=request.import_batch_id,
            status="ready_for_import",
            imported=True,
            plan=plan,
        )


class _ReportService(ReportService):
    def __init__(self) -> None:
        self.last_daily_date = ""

    def build_meituan_daily_report(self, request):
        self.last_daily_date = request.report_date
        return ProcessingResult(
            module="anta_meituan_daily",
            output_rows=[{"name": "sales", "value": "100"}],
            summary={"report_date": request.report_date},
            warnings=[],
        )


class _FailingReportService(ReportService):
    def __init__(self) -> None:
        pass

    def build_meituan_daily_report(self, request):
        raise ValidationError("foundation data missing")


class _AIContentService(AIContentService):
    def __init__(self) -> None:
        self.last_task_type = ""

    def build_content_pack(self, request):
        self.last_task_type = request.task_type
        return ProcessingResult(
            module="p2_content_center",
            output_rows=[{"AI title": "copy"}],
            summary={"task_type": request.task_type},
            warnings=[],
        )


def _data_import_task() -> TaskRequest:
    return TaskRequest(
        task_id=1,
        task_type=TaskType.DATA_IMPORT,
        created_by="admin",
        payload={
            "import_batch_id": "batch-1",
            "metadata": {
                "business_unit": "anta_retail_team",
                "brand_id": "anta_kids",
                "brand_name": "Anta Kids",
                "platform": "meituan",
                "channel": "instant_retail",
                "project_code": "p1_p2_anta_meituan",
                "declared_file_type": "product_order",
                "data_start_date": "20260725",
                "data_end_date": "20260725",
                "uploaded_by": "admin",
            },
            "rows": [_product_row()],
            "known_store_ids": ["S1"],
            "known_product_codes": ["SKU1"],
            "original_file_name": "source.csv",
            "stored_file_path": "runtime/intake/source.csv",
            "file_sha256": "0" * 64,
        },
        created_time="2026-07-30T17:05:00+08:00",
    )


def _report_task() -> TaskRequest:
    return TaskRequest(
        task_id=2,
        task_type=TaskType.REPORT_GENERATE,
        created_by="admin",
        payload={
            "report_period": "daily",
            "brand_id": "anta_kids",
            "platform": "meituan",
            "channel": "instant_retail",
            "report_date": "20260725",
        },
        created_time="2026-07-30T17:05:00+08:00",
    )


def _ai_content_task() -> TaskRequest:
    return TaskRequest(
        task_id=3,
        task_type=TaskType.AI_CONTENT_GENERATE,
        created_by="admin",
        payload={
            "brand_id": "anta_kids",
            "brand_name": "Anta Kids",
            "platform": "meituan",
            "channel": "instant_retail",
            "start_date": "20260720",
            "end_date": "20260726",
            "task_type": "social_copy",
            "output_count": 1,
            "brand_profile": "Anta Kids brand profile for unit tests.",
            "forbidden_words": ["absolute"],
        },
        created_time="2026-07-30T17:05:00+08:00",
    )


def _product_row() -> dict[str, str]:
    return {
        "日期": "20260725",
        "订单编号": "O1",
        "下单时间": "2026-07-25 10:00:00",
        "店铺名称": "Shanghai Store",
        "店铺ID": "S1",
        "店铺所在城市": "Shanghai",
        "订单状态": "订单完成",
        "商品分类": "Shoes",
        "商品名称": "Anta Kids UFO8",
        "UPC码": "SKU1",
        "商品SKU码": "SKU1",
        "商品销售数量": "1",
        "商品实付销售额": "100.00",
        "部分退款商品金额": "",
    }


if __name__ == "__main__":
    unittest.main()
