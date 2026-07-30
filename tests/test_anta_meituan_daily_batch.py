from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from tools.generate_anta_meituan_daily_batch import generate_batch
from tools.run_meituan_plugin_to_daily_e2e import run_flow


class AntaMeituanDailyBatchTests(unittest.TestCase):
    def test_generate_batch_writes_available_daily_reports_and_missing_index(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            downloads = root / "downloads"
            outputs = root / "outputs"
            downloads.mkdir()
            _write_csv(downloads / "商品数据_20260720-20260721_全店数据.csv", _product_rows())
            _write_csv(downloads / "门店财务明细_20260721_20260721.csv", _finance_rows())
            _write_csv(downloads / "门店流量明细_20260721_20260721.csv", _traffic_rows())
            _write_csv(downloads / "20260720-20260721-全店数据-评价分析明细.csv", _review_rows())

            results = generate_batch("20260720", "20260721", downloads, outputs)

            self.assertEqual([item.status for item in results], ["generated", "generated"])
            self.assertTrue((outputs / "anta_meituan_daily_report_20260720.csv").exists())
            self.assertTrue((outputs / "anta_meituan_daily_report_20260721.csv").exists())
            self.assertTrue((outputs / "anta_meituan_daily_batch_index.csv").exists())

    def test_generate_batch_marks_missing_product_days(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            downloads = root / "downloads"
            outputs = root / "outputs"
            downloads.mkdir()
            _write_csv(downloads / "商品数据_20260720-20260720_全店数据.csv", [_product_rows()[0]])

            results = generate_batch("20260719", "20260720", downloads, outputs)

            self.assertEqual(results[0].status, "missing")
            self.assertEqual(results[1].status, "generated")

    def test_plugin_nested_downloads_sync_and_generate_daily_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            plugin_root = root / "plugin_downloads" / "meituan_auto_download"
            nested = plugin_root / "anta_kids" / "instant_retail" / "20260721"
            _write_csv(nested / "product_order" / "商品数据_20260720-20260721_全店数据.csv", _product_rows())
            _write_csv(nested / "store_finance" / "门店财务明细_20260721_20260721.csv", _finance_rows())
            _write_csv(nested / "store_traffic" / "门店流量明细_20260721_20260721.csv", _traffic_rows())
            _write_csv(nested / "service_review" / "20260720-20260721-全店数据-评价分析明细.csv", _review_rows())

            result = run_flow(root, plugin_root, "20260720", "20260721")

            self.assertEqual(len(result.synced_files), 4)
            self.assertEqual([item.status for item in result.daily_results], ["generated", "generated"])
            self.assertTrue((result.output_root / "anta_meituan_daily_report_20260721.csv").exists())
            self.assertTrue((result.intake_root / "anta_kids" / "instant_retail" / "20260721" / "product_order").exists())


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _product_rows() -> list[dict[str, str]]:
    return [
        {
            "日期": "20260720-20260721",
            "订单编号": "O1",
            "下单时间": "2026-07-20 10:00:00",
            "店铺名称": "上海店",
            "店铺ID": "S1",
            "店铺所在城市": "上海",
            "订单状态": "订单完成",
            "商品分类": "鞋服",
            "商品名称": "UFO跑鞋",
            "UPC码": "U1",
            "商品SKU码": "SKU1",
            "商品销售数量": "1",
            "商品实付销售额": "100",
        },
        {
            "日期": "20260720-20260721",
            "订单编号": "O2",
            "下单时间": "2026-07-21 11:00:00",
            "店铺名称": "北京店",
            "店铺ID": "S2",
            "店铺所在城市": "北京",
            "订单状态": "订单完成",
            "商品分类": "鞋服",
            "商品名称": "泳装套装",
            "UPC码": "U2",
            "商品SKU码": "SKU2",
            "商品销售数量": "2",
            "商品实付销售额": "200",
        },
    ]


def _finance_rows() -> list[dict[str, str]]:
    return [
        {
            "开始时间": "20260721",
            "结束时间": "20260721",
            "商家ID": "S2",
            "商家名称": "北京店",
            "省份": "北京",
            "城市": "北京",
            "实付交易额": "200",
            "有效订单数": "1",
            "实付单均价": "200",
        }
    ]


def _traffic_rows() -> list[dict[str, str]]:
    return [
        {
            "开始时间": "20260721",
            "结束时间": "20260721",
            "商家ID": "S2",
            "商家名称": "北京店",
            "城市": "北京",
            "曝光人数": "100",
            "入店人数": "10",
            "下单人数": "1",
            "入店转化率": "10",
            "下单转化率": "10",
        }
    ]


def _review_rows() -> list[dict[str, str]]:
    return [
        {
            "评价提交日期": "20260720",
            "店铺名称": "上海店",
            "店铺ID": "S1",
            "店铺所在城市": "上海",
            "订单商品": "UFO跑鞋",
            "用户评价": "不错",
            "商家评分": "5",
            "配送体验评分": "5",
        }
    ]


if __name__ == "__main__":
    unittest.main()
