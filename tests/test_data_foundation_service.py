from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from backend.repositories.sqlite.foundation_repository import SQLiteFoundationRepository
from backend.services.data_foundation_service import (
    DataFoundationProcessRequest,
    DataFoundationService,
)
from intranet_app.data_foundation import UploadMetadata
from intranet_app.domain import ValidationError
from intranet_app.storage import AppStorage


class DataFoundationServiceTests(unittest.TestCase):
    def test_normal_rows_are_validated_saved_and_imported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            storage = _storage(Path(tmp_dir))
            repository = SQLiteFoundationRepository(storage)
            service = DataFoundationService(repository)

            result = service.process_rows(_request(Path(tmp_dir), rows=_valid_rows()))
            rows = repository.query_foundation_rows("anta_kids", "meituan", "instant_retail", "product_order")

        self.assertEqual(result.status, "ready_for_import")
        self.assertTrue(result.imported)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["商品SKU码"], "2000000447168")

    def test_empty_file_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            service = DataFoundationService(SQLiteFoundationRepository(_storage(Path(tmp_dir))))

            with self.assertRaises(ValidationError):
                service.process_rows(_request(Path(tmp_dir), rows=[]))

    def test_missing_required_field_returns_validation_failed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            service = DataFoundationService(SQLiteFoundationRepository(_storage(Path(tmp_dir))))
            rows = _valid_rows()
            rows[0].pop("商品SKU码")

            result = service.process_rows(_request(Path(tmp_dir), rows=rows))

        self.assertEqual(result.status, "validation_failed")
        self.assertFalse(result.imported)
        self.assertIn("missing required field", result.plan.validation.errors[0])

    def test_invalid_amount_returns_validation_failed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            service = DataFoundationService(SQLiteFoundationRepository(_storage(Path(tmp_dir))))
            rows = _valid_rows()
            rows[0]["商品实付销售额"] = "not-a-number"

            result = service.process_rows(_request(Path(tmp_dir), rows=rows))

        self.assertEqual(result.status, "validation_failed")
        self.assertFalse(result.imported)
        self.assertTrue(any("must be decimal" in message for message in result.plan.validation.errors))

    def test_invalid_metadata_date_range_is_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            _metadata(start_date="20260726", end_date="20260720")


def _storage(root: Path) -> AppStorage:
    storage = AppStorage(root / "runtime" / "test.sqlite3")
    storage.initialize("test-password")
    return storage


def _request(root: Path, rows: list[dict[str, str]]) -> DataFoundationProcessRequest:
    stored_file = root / "repository_test.csv"
    stored_file.write_text("source", encoding="utf-8")
    return DataFoundationProcessRequest(
        import_batch_id="batch_service_test",
        metadata=_metadata(),
        rows=rows,
        known_store_ids=("20814419",),
        known_product_codes=("2000000447168",),
        original_file_name="repository_test.csv",
        stored_file_path=stored_file,
        file_sha256="0" * 64,
    )


def _metadata(start_date: str = "20260720", end_date: str = "20260726") -> UploadMetadata:
    return UploadMetadata(
        business_unit="anta_retail_team",
        brand_id="anta_kids",
        brand_name="安踏儿童",
        platform="meituan",
        channel="instant_retail",
        project_code="p1_p2_anta_meituan",
        declared_file_type="product_order",
        data_start_date=start_date,
        data_end_date=end_date,
        uploaded_by="admin",
    )


def _valid_rows() -> list[dict[str, str]]:
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
            "部分退款商品金额": "",
        }
    ]


if __name__ == "__main__":
    unittest.main()
