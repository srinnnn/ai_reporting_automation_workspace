from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from intranet_app.app import IntranetApp, _source_date_range
from intranet_app.auth import PasswordHash
from intranet_app.config import AppConfig
from intranet_app.processors.anta_meituan_reporting import (
    MeituanReportSources,
    build_meituan_daily_report,
    build_meituan_weekly_report,
)
from intranet_app.storage import UserRecord


class AntaMeituanReportingTests(unittest.TestCase):
    def test_build_daily_report_contains_brand_delivery_sections(self) -> None:
        result = build_meituan_daily_report(_sources(), "20260725")

        sections = {row["板块"] for row in result.output_rows}
        self.assertEqual(result.summary["报表类型"], "安踏美团日报")
        self.assertIn("快报文案", sections)
        self.assertIn("核心指标", sections)
        self.assertIn("近7天TOP门店", sections)
        self.assertIn("近7天TOP商品", sections)
        self.assertIn("流量转化", sections)
        self.assertNotIn("评价服务", sections)
        self.assertNotIn("下周选品建议", sections)
        self.assertNotIn("内容文案建议", sections)
        self.assertTrue(any(row["名称"] == "销售额" and row["数值"] == "300.00" for row in result.output_rows))
        self.assertTrue(any("安踏儿童美团即时零售销售快报" in row["数值"] for row in result.output_rows))

    def test_build_weekly_report_aggregates_multi_day_rows(self) -> None:
        result = build_meituan_weekly_report(_sources(), "20260720", "20260726")

        self.assertEqual(result.summary["报表类型"], "安踏美团周报")
        self.assertEqual(result.summary["销售额"], "500.00")
        self.assertTrue(any(row["板块"] == "本周TOP商品" and row["名称"] == "UFO跑鞋" for row in result.output_rows))
        self.assertTrue(any(row["板块"] == "评价服务" for row in result.output_rows))
        self.assertTrue(any(row["板块"] == "下周选品建议" and row["名称"] == "UFO跑鞋" for row in result.output_rows))
        self.assertTrue(any(row["板块"] == "内容文案建议" and row["名称"] == "UFO跑鞋" for row in result.output_rows))
        self.assertTrue(any("AI不编造未提供卖点" in row["说明"] for row in result.output_rows))

    def test_build_weekly_report_derives_missing_finance_unit_price(self) -> None:
        sources = _sources()
        finance_rows = [{key: value for key, value in row.items() if key != "实付单均价"} for row in sources.finance_rows]

        result = build_meituan_weekly_report(
            MeituanReportSources(sources.product_rows, finance_rows, sources.traffic_rows, sources.review_rows),
            "20260720",
            "20260726",
        )

        self.assertEqual(result.summary["报表类型"], "安踏美团周报")
        self.assertEqual(result.summary["销售额"], "500.00")

    def test_source_date_range_reads_date_ranges(self) -> None:
        rows = [{"日期": "20260720-20260726"}]

        start_date, end_date = _source_date_range(rows, "日期")

        self.assertEqual(start_date, "20260720")
        self.assertEqual(end_date, "20260726")

    def test_anta_reporting_page_exposes_meituan_delivery_buttons(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            (root / "materials").mkdir()
            app = IntranetApp(_config(root))
            app.storage = _EmptyStorage()
            user = UserRecord(1, "admin", "系统管理员", "管理员", PasswordHash("salt", "digest"))

            page = app._anta_reporting_page(user, "")

            self.assertIn("美团日报交付版", page)
            self.assertIn("下周选品建议", page)
            self.assertIn("内容文案建议", page)
            self.assertIn('name="report_date"', page)
            self.assertIn('type="date"', page)
            self.assertIn('action="/anta-reporting/meituan-daily/run"', page)
            self.assertIn('action="/anta-reporting/meituan-weekly/run"', page)

    def test_selected_meituan_report_date_requires_valid_date(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            (root / "materials").mkdir()
            app = IntranetApp(_config(root))

            self.assertEqual(app._selected_meituan_report_date({"report_date": ["2026-07-27"]}), "20260727")
            with self.assertRaises(Exception):
                app._selected_meituan_report_date({"report_date": [""]})


def _sources() -> MeituanReportSources:
    product_rows = [
        _product_row("20260725", "O1", "S1", "上海店", "上海", "UFO跑鞋", "SKU1", "2", "300"),
        _product_row("20260724", "O2", "S2", "北京店", "北京", "泳装套装", "SKU2", "1", "200"),
    ]
    finance_rows = [
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
    ]
    traffic_rows = [
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
    ]
    review_rows = [
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
    ]
    return MeituanReportSources(product_rows, finance_rows, traffic_rows, review_rows)


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


class _EmptyStorage:
    def list_jobs(self) -> list[object]:
        return []

    def list_project_feedback(self) -> dict[str, object]:
        return {}


def _config(root: Path) -> AppConfig:
    return AppConfig(
        host="127.0.0.1",
        port=8765,
        secret_key="test-secret",
        database_path=root / "runtime" / "intranet.sqlite3",
        upload_dir=root / "runtime" / "uploads",
        result_dir=root / "runtime" / "results",
        template_root=root / "materials",
        default_admin_password="admin123",
    )


if __name__ == "__main__":
    unittest.main()
