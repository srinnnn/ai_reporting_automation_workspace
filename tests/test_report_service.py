from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from typing import Any

from backend.repositories.interfaces import FoundationCheckRecord, FoundationRepository, ReportCreate, ReportRepository
from backend.services.report_service import (
    MeituanReportRequest,
    MeituanWeeklyReportRequest,
    ReportSaveRequest,
    ReportService,
)
from intranet_app.domain import ProcessingResult, ValidationError
from intranet_app.storage import JobRecord


class ReportServiceTests(unittest.TestCase):
    def test_builds_daily_report_from_foundation_repository(self) -> None:
        service = ReportService(_FoundationRepository(_sources()))

        result = service.build_meituan_daily_report(_daily_request("20260725"))

        self.assertEqual(result.summary["报表类型"], "安踏美团日报")
        self.assertTrue(any(row["板块"] == "快报文案" for row in result.output_rows))
        self.assertTrue(any(row["名称"] == "销售额" and row["数值"] == "300.00" for row in result.output_rows))

    def test_builds_weekly_report_from_foundation_repository(self) -> None:
        service = ReportService(_FoundationRepository(_sources()))

        result = service.build_meituan_weekly_report(_weekly_request("20260720", "20260726"))

        self.assertEqual(result.summary["报表类型"], "安踏美团周报")
        self.assertEqual(result.summary["销售额"], "500.00")
        self.assertTrue(any(row["板块"] == "下周选品建议" for row in result.output_rows))

    def test_empty_foundation_product_data_fails_closed(self) -> None:
        sources = _sources()
        sources["product_order"] = []
        service = ReportService(_FoundationRepository(sources))

        with self.assertRaises(ValidationError):
            service.build_meituan_daily_report(_daily_request("20260725"))

    def test_invalid_date_is_rejected_by_existing_processor(self) -> None:
        service = ReportService(_FoundationRepository(_sources()))

        with self.assertRaises(ValidationError):
            service.build_meituan_daily_report(_daily_request("2026-99-99"))

    def test_missing_required_field_is_rejected_by_existing_processor(self) -> None:
        sources = _sources()
        sources["product_order"] = [dict(sources["product_order"][0])]
        sources["product_order"][0].pop("订单编号")
        service = ReportService(_FoundationRepository(sources))

        with self.assertRaises(ValidationError):
            service.build_meituan_weekly_report(_weekly_request("20260720", "20260726"))

    def test_report_result_can_be_saved_through_report_repository(self) -> None:
        report_repository = _ReportRepository()
        service = ReportService(_FoundationRepository(_sources()), report_repository)
        result = service.build_meituan_daily_report(_daily_request("20260725"))
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            input_file = root / "input.csv"
            result_file = root / "result.csv"
            input_file.write_text("input", encoding="utf-8")
            result_file.write_text("result", encoding="utf-8")

            report_id = service.save_report_result(
                ReportSaveRequest(
                    module="anta_meituan_reporting",
                    title="安踏美团日报",
                    brand="安踏儿童",
                    business_type="日报",
                    created_by="admin",
                    input_file=input_file,
                    result_file=result_file,
                ),
                result,
            )

        self.assertEqual(report_id, 1)
        self.assertEqual(report_repository.saved_request.title, "安踏美团日报")

    def test_monthly_report_is_explicitly_not_foundation_backed_yet(self) -> None:
        service = ReportService(_FoundationRepository(_sources()))

        with self.assertRaises(NotImplementedError):
            service.build_meituan_monthly_report()


class _FoundationRepository(FoundationRepository):
    def __init__(self, rows_by_type: dict[str, list[dict[str, str]]]) -> None:
        self.rows_by_type = rows_by_type

    def save_foundation_check(self, record: FoundationCheckRecord) -> None:
        raise NotImplementedError

    def save_foundation_rows(self, import_batch_id: str, plan: Any) -> None:
        raise NotImplementedError

    def query_foundation_rows(
        self,
        brand_id: str,
        platform: str,
        channel: str,
        file_type: str,
    ) -> list[dict[str, str]]:
        return [dict(row) for row in self.rows_by_type.get(file_type, [])]


class _ReportRepository(ReportRepository):
    def __init__(self) -> None:
        self.saved_request: ReportCreate | None = None

    def save_report(self, request: ReportCreate) -> int:
        self.saved_request = request
        return 1

    def get_report(self, report_id: int) -> JobRecord | None:
        return None


def _daily_request(report_date: str) -> MeituanReportRequest:
    return MeituanReportRequest(
        brand_id="anta_kids",
        platform="meituan",
        channel="instant_retail",
        report_date=report_date,
    )


def _weekly_request(start_date: str, end_date: str) -> MeituanWeeklyReportRequest:
    return MeituanWeeklyReportRequest(
        brand_id="anta_kids",
        platform="meituan",
        channel="instant_retail",
        start_date=start_date,
        end_date=end_date,
    )


def _sources() -> dict[str, list[dict[str, str]]]:
    return {
        "product_order": [
            _product_row("20260725", "O1", "S1", "上海店", "上海", "UFO跑鞋", "SKU1", "2", "300"),
            _product_row("20260724", "O2", "S2", "北京店", "北京", "泳装套装", "SKU2", "1", "200"),
        ],
        "store_finance": [
            {
                "开始时间": "20260725",
                "结束时间": "20260725",
                "商家ID": "S1",
                "商家名称": "上海店",
                "省份": "上海",
                "城市": "上海",
                "实付交易额": "300",
                "有效订单数": "1",
                "实付单均价": "300",
            },
            {
                "开始时间": "20260724",
                "结束时间": "20260724",
                "商家ID": "S2",
                "商家名称": "北京店",
                "省份": "北京",
                "城市": "北京",
                "实付交易额": "200",
                "有效订单数": "1",
                "实付单均价": "200",
            },
        ],
        "store_traffic": [
            {
                "开始时间": "20260725",
                "结束时间": "20260725",
                "商家ID": "S1",
                "商家名称": "上海店",
                "城市": "上海",
                "曝光人数": "1000",
                "入店人数": "100",
                "下单人数": "10",
                "入店转化率": "10",
                "下单转化率": "10",
            }
        ],
        "service_review": [
            {
                "评价提交日期": "20260725",
                "店铺名称": "上海店",
                "店铺ID": "S1",
                "店铺所在城市": "上海",
                "订单商品": "UFO跑鞋",
                "用户评价": "不错",
                "商家评分": "5",
                "配送体验评分": "5",
            }
        ],
    }


def _product_row(
    row_date: str,
    order_id: str,
    store_id: str,
    store_name: str,
    city: str,
    product_name: str,
    sku: str,
    quantity: str,
    amount: str,
) -> dict[str, str]:
    return {
        "日期": row_date,
        "订单编号": order_id,
        "下单时间": f"{row_date} 10:00:00",
        "店铺名称": store_name,
        "店铺ID": store_id,
        "店铺所在城市": city,
        "订单状态": "订单完成",
        "商品分类": "鞋服",
        "商品名称": product_name,
        "UPC码": sku,
        "商品SKU码": sku,
        "商品销售数量": quantity,
        "商品实付销售额": amount,
    }


if __name__ == "__main__":
    unittest.main()
