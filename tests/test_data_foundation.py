from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from intranet_app.data_foundation import (
    UploadMetadata,
    build_ingestion_plan,
    recognize_file_type,
    validate_required_fields,
    get_field_mapping,
)
from intranet_app.domain import ValidationError
from intranet_app.storage import AppStorage


class DataFoundationRuleTests(unittest.TestCase):
    def test_build_ingestion_plan_for_meituan_product_order(self) -> None:
        metadata = _metadata("product_order")
        rows = [
            {
                "日期": "\t20260720-20260726",
                "订单编号": "2602227131342725859\t",
                "下单时间": "2026-07-25 14:58:52\t",
                "店铺名称": "安踏儿童（高新万达店）\t",
                "店铺ID": "20814419\t",
                "店铺所在城市": "济南\t",
                "订单状态": "订单完成",
                "商品分类": "户外运动>水上运动\t",
                "商品名称": "安踏儿童泳镜\t",
                "UPC码": "2000000447168\t",
                "商品SKU码": "2000000447168\t",
                "商品销售数量": "2\t",
                "商品实付销售额": "95.00",
                "部分退款商品金额": "",
            }
        ]

        plan = build_ingestion_plan(
            metadata,
            rows,
            known_store_ids=("20814419",),
            known_product_codes=("2000000447168",),
        )

        self.assertTrue(plan.validation.passed)
        self.assertEqual(plan.recognition.file_type, "product_order")
        self.assertEqual(plan.target_table, "fact_order_product")
        self.assertEqual(plan.brand_match.decision, "auto_pass")
        self.assertEqual(plan.normalized_rows[0]["store_id"], "20814419")
        self.assertEqual(plan.normalized_rows[0]["refund_amount"], "0")

    def test_missing_required_field_is_rejected(self) -> None:
        mapping = get_field_mapping("meituan", "product_order")
        result = validate_required_fields(("订单编号", "店铺名称"), mapping)

        self.assertFalse(result.passed)
        self.assertIn("missing required field", result.errors[0])

    def test_empty_rows_are_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            build_ingestion_plan(_metadata("product_order"), [], (), ())

    def test_unknown_file_type_confidence_is_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            recognize_file_type(("无关字段A", "无关字段B"), "meituan")

    def test_brand_mismatch_requires_rejection(self) -> None:
        metadata = _metadata("product_order")
        rows = [
            {
                "日期": "20260720-20260726",
                "订单编号": "1",
                "下单时间": "2026-07-25 14:58:52",
                "店铺名称": "其他品牌门店",
                "店铺ID": "other-store",
                "店铺所在城市": "上海",
                "订单状态": "订单完成",
                "商品分类": "测试",
                "商品名称": "其他品牌商品",
                "UPC码": "other-upc",
                "商品SKU码": "other-sku",
                "商品销售数量": "1",
                "商品实付销售额": "10.00",
                "部分退款商品金额": "0",
            }
        ]

        plan = build_ingestion_plan(metadata, rows, known_store_ids=("20814419",), known_product_codes=("2000000447168",))

        self.assertFalse(plan.validation.passed)
        self.assertEqual(plan.brand_match.decision, "reject")


class DataFoundationStorageTests(unittest.TestCase):
    def test_initialize_creates_foundation_tables(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            database_path = Path(tmp_dir) / "runtime" / "test.sqlite3"
            storage = AppStorage(database_path)
            storage.initialize("test-password")

            connection = sqlite3.connect(database_path)
            try:
                tables = {
                    str(row[0])
                    for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
                }
            finally:
                connection.close()

        expected_tables = {
            "import_batches",
            "source_files",
            "field_mapping_rules",
            "validation_reports",
            "missing_data_items",
            "fact_order_product",
            "fact_store_finance",
            "fact_store_traffic",
            "fact_service_review",
            "dim_product",
            "dim_store",
            "target_plan",
            "dim_campaign",
            "dim_platform_shop",
            "dim_channel_product",
        }
        self.assertTrue(expected_tables.issubset(tables))

    def test_save_foundation_check_persists_batch_and_reports(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            database_path = root / "runtime" / "test.sqlite3"
            stored_file = root / "upload.csv"
            stored_file.write_text("x", encoding="utf-8")
            storage = AppStorage(database_path)
            storage.initialize("test-password")
            storage.save_foundation_check(
                import_batch_id="batch_test",
                metadata=_metadata("product_order"),
                original_file_name="upload.csv",
                stored_file_path=stored_file,
                file_sha256="abc123",
                recognized_file_type="product_order",
                row_count=1,
                status="manual_review",
                brand_match_score=70,
                validation_errors=("missing product library",),
                validation_warnings=("manual review required",),
            )

            connection = sqlite3.connect(database_path)
            try:
                batch = connection.execute(
                    "SELECT status, brand_match_score FROM import_batches WHERE import_batch_id = ?",
                    ("batch_test",),
                ).fetchone()
                report_count = connection.execute(
                    "SELECT COUNT(*) FROM validation_reports WHERE import_batch_id = ?",
                    ("batch_test",),
                ).fetchone()[0]
            finally:
                connection.close()

        self.assertEqual(batch, ("manual_review", 70))
        self.assertEqual(report_count, 2)

    def test_passed_foundation_plan_writes_fact_rows_for_reports(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            database_path = root / "runtime" / "test.sqlite3"
            stored_file = root / "upload.csv"
            stored_file.write_text("x", encoding="utf-8")
            storage = AppStorage(database_path)
            storage.initialize("test-password")
            metadata = _metadata("product_order")
            plan = build_ingestion_plan(
                metadata,
                _product_order_rows(),
                known_store_ids=("20814419",),
                known_product_codes=("2000000447168",),
            )
            storage.save_foundation_check(
                import_batch_id="batch_fact",
                metadata=metadata,
                original_file_name="upload.csv",
                stored_file_path=stored_file,
                file_sha256="abc123",
                recognized_file_type=plan.recognition.file_type,
                row_count=len(plan.normalized_rows),
                status="ready_for_import",
                brand_match_score=plan.brand_match.total_score,
                validation_errors=plan.validation.errors,
                validation_warnings=plan.validation.warnings,
            )

            storage.save_foundation_fact_rows("batch_fact", plan)
            loaded_rows = storage.load_meituan_foundation_rows("anta_kids", "meituan", "instant_retail", "product_order")

        self.assertEqual(len(loaded_rows), 1)
        self.assertEqual(loaded_rows[0]["订单编号"], "2602227131342725859")
        self.assertEqual(loaded_rows[0]["商品实付销售额"], "95.00")

    def test_store_finance_foundation_rows_include_derived_unit_price(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            database_path = root / "runtime" / "test.sqlite3"
            stored_file = root / "finance.csv"
            stored_file.write_text("x", encoding="utf-8")
            storage = AppStorage(database_path)
            storage.initialize("test-password")
            metadata = _metadata("store_finance")
            plan = build_ingestion_plan(
                metadata,
                _store_finance_rows(),
                known_store_ids=("20814419",),
                known_product_codes=(),
            )
            storage.save_foundation_check(
                import_batch_id="batch_finance",
                metadata=metadata,
                original_file_name="finance.csv",
                stored_file_path=stored_file,
                file_sha256="abc123",
                recognized_file_type=plan.recognition.file_type,
                row_count=len(plan.normalized_rows),
                status="ready_for_import",
                brand_match_score=plan.brand_match.total_score,
                validation_errors=plan.validation.errors,
                validation_warnings=plan.validation.warnings,
            )

            storage.save_foundation_fact_rows("batch_finance", plan)
            loaded_rows = storage.load_meituan_foundation_rows("anta_kids", "meituan", "instant_retail", "store_finance")

        self.assertEqual(len(loaded_rows), 1)
        self.assertEqual(loaded_rows[0]["实付交易额"], "300.00")
        self.assertEqual(loaded_rows[0]["有效订单数"], "2")
        self.assertEqual(loaded_rows[0]["实付单均价"], "150.00")


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
        uploaded_by="tester",
    )


def _product_order_rows() -> list[dict[str, str]]:
    return [
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
            "部分退款商品金额": "0",
        }
    ]


def _store_finance_rows() -> list[dict[str, str]]:
    return [
        {
            "开始时间": "20260725",
            "结束时间": "20260725",
            "商家ID": "20814419",
            "商家名称": "安踏儿童（高新万达店）",
            "省份": "山东",
            "城市": "济南",
            "收入": "280.00",
            "营业额": "320.00",
            "实付交易额": "300.00",
            "有效订单数": "2",
        }
    ]


if __name__ == "__main__":
    unittest.main()
