from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from backend.repositories.interfaces import (
    AutomationTaskCreate,
    ReportCreate,
    UserCreate,
)
from backend.repositories.sqlite.foundation_repository import SQLiteFoundationRepository
from backend.repositories.sqlite.report_repository import SQLiteReportRepository
from backend.repositories.sqlite.task_repository import SQLiteTaskRepository
from backend.repositories.sqlite.user_repository import SQLiteUserRepository
from intranet_app.data_foundation import UploadMetadata, build_ingestion_plan
from intranet_app.storage import AppStorage


class RepositoryAdapterTests(unittest.TestCase):
    def test_repositories_can_initialize(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            storage = _storage(Path(tmp_dir))

            self.assertIsInstance(SQLiteUserRepository(storage), SQLiteUserRepository)
            self.assertIsInstance(SQLiteFoundationRepository(storage), SQLiteFoundationRepository)
            self.assertIsInstance(SQLiteReportRepository(storage), SQLiteReportRepository)
            self.assertIsInstance(SQLiteTaskRepository(storage), SQLiteTaskRepository)

    def test_user_query_and_verify_use_legacy_storage(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            storage = _storage(Path(tmp_dir))
            repository = SQLiteUserRepository(storage)

            admin = repository.get_user("admin")

            self.assertIsNotNone(admin)
            self.assertTrue(repository.verify_user("admin", "test-password"))
            self.assertFalse(repository.verify_user("admin", "wrong-password"))

    def test_create_user_maps_to_default_admin_without_schema_change(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            storage = _storage(Path(tmp_dir))
            repository = SQLiteUserRepository(storage)

            user = repository.create_user(UserCreate("admin", "new-password", "Admin", "admin"))

            self.assertEqual(user.username, "admin")
            self.assertTrue(repository.verify_user("admin", "new-password"))

    def test_foundation_rows_can_be_saved_and_queried(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            storage = _storage(Path(tmp_dir))
            repository = SQLiteFoundationRepository(storage)
            plan = _product_order_plan()

            repository.save_foundation_rows("batch_repository", plan)
            rows = repository.query_foundation_rows("anta_kids", "meituan", "instant_retail", "product_order")

            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["商品SKU码"], "2000000447168")

    def test_report_can_be_saved_and_loaded(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            storage = _storage(root)
            input_file = root / "input.csv"
            result_file = root / "result.csv"
            input_file.write_text("input", encoding="utf-8")
            result_file.write_text("result", encoding="utf-8")
            repository = SQLiteReportRepository(storage)

            report_id = repository.save_report(
                ReportCreate(
                    module="anta_meituan_daily",
                    title="安踏美团日报",
                    brand="安踏儿童",
                    business_type="日报",
                    created_by="admin",
                    input_file=input_file,
                    result_file=result_file,
                    summary={"rows": "1"},
                    warnings=[],
                )
            )
            report = repository.get_report(report_id)

            self.assertIsNotNone(report)
            self.assertEqual(report.title, "安踏美团日报")

    def test_task_status_update_uses_existing_enabled_flag(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            storage = _storage(Path(tmp_dir))
            repository = SQLiteTaskRepository(storage)

            task_id = repository.create_task(
                AutomationTaskCreate(
                    task_name="Repository日报任务",
                    business_unit="anta_retail_team",
                    brand_id="anta_kids",
                    brand_name="安踏儿童",
                    platform="meituan",
                    channel="instant_retail",
                    file_type="product_order",
                    frequency="daily",
                    scheduled_time="09:30",
                    date_window="yesterday",
                    enabled=True,
                    output_folder="runtime/results",
                    owner="admin",
                    notes="repository adapter test",
                )
            )

            repository.update_task_status(task_id, "disabled")
            task = repository.get_task(task_id)

            self.assertIsNotNone(task)
            self.assertFalse(task.enabled)


def _storage(root: Path) -> AppStorage:
    storage = AppStorage(root / "runtime" / "test.sqlite3")
    storage.initialize("test-password")
    return storage


def _product_order_plan() -> object:
    return build_ingestion_plan(
        _metadata("product_order"),
        [
            {
                "日期": "20260720-20260726",
                "订单编号": "2602227131342725859",
                "下单时间": "2026-07-25 14:58:52",
                "店铺名称": "安踏儿童（高新万达店）",
                "店铺ID": "20814419",
                "店铺所在城市": "济南",
                "订单状态": "订单完成",
                "商品分类": "户外运动>水上运动",
                "商品名称": "安踏儿童泳镜",
                "UPC码": "2000000447168",
                "商品SKU码": "2000000447168",
                "商品销售数量": "2",
                "商品实付销售额": "95.00",
                "部分退款商品金额": "",
            }
        ],
        known_store_ids=("20814419",),
        known_product_codes=("2000000447168",),
    )


def _metadata(file_type: str) -> UploadMetadata:
    return UploadMetadata(
        business_unit="anta_retail_team",
        brand_id="anta_kids",
        brand_name="安踏儿童",
        platform="meituan",
        channel="instant_retail",
        project_code="p1_p2_anta_meituan",
        declared_file_type=file_type,
        data_start_date="20260720",
        data_end_date="20260726",
        uploaded_by="admin",
    )


if __name__ == "__main__":
    unittest.main()
