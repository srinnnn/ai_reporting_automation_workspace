from __future__ import annotations

import unittest

from intranet_app.processors import anta_reporting


class AntaReportingTests(unittest.TestCase):
    def test_build_weekly_report(self) -> None:
        meituan = anta_reporting.ReportSource(
            name="美团周数据.xlsx",
            rows=[
                {
                    "订单状态": "订单完成",
                    "订单编号": "M1",
                    "商品名称": "跑鞋A",
                    "商品销售数量": "2",
                    "商品实付销售额": "200.50",
                },
                {
                    "订单状态": "订单完成",
                    "订单编号": "M2",
                    "商品名称": "跑鞋B",
                    "商品销售数量": "1",
                    "商品实付销售额": "99.50",
                },
            ],
        )
        jd = anta_reporting.ReportSource(
            name="京东周数据.xlsx",
            rows=[
                {"商品名称": "跑鞋A", "实付销售额": "300", "商品销量": "3"},
            ],
        )

        result = anta_reporting.build_weekly_report(meituan, jd)

        self.assertEqual(result.summary["报表类型"], "安踏周报初稿")
        self.assertIn({"报表类型": "周报", "模块": "核心指标", "平台": "美团", "指标": "销售额", "数值": "300.00", "说明": "系统按已归档原始数据自动汇总"}, result.output_rows)
        self.assertTrue(any(row["模块"] == "TOP商品" for row in result.output_rows))

    def test_build_monthly_report(self) -> None:
        products = anta_reporting.ReportSource(
            name="商品数据.csv",
            rows=[
                {
                    "订单状态": "订单完成",
                    "订单编号": "M1",
                    "商品名称": "跑鞋A",
                    "商品销售数量": "2",
                    "商品实付销售额": "200",
                }
            ],
        )
        stores = anta_reporting.ReportSource(
            name="门店信息汇总.xlsx",
            rows=[
                {"门店ID": "S1", "营业状态": "营业中", "所在城市": "上海"},
                {"门店ID": "S2", "营业状态": "休息", "所在城市": "北京"},
            ],
        )
        finance = anta_reporting.ReportSource(
            name="门店财务明细.csv",
            rows=[
                {"收入": "100", "营业额": "200", "实付交易额": "180", "有效订单数": "2", "已取消订单数": "1"},
            ],
        )

        result = anta_reporting.build_monthly_report(products, stores, finance)

        self.assertEqual(result.summary["报表类型"], "安踏月报初稿")
        self.assertTrue(any(row["平台"] == "门店" and row["指标"] == "门店数" and row["数值"] == "2" for row in result.output_rows))
        self.assertTrue(any(row["平台"] == "财务" and row["指标"] == "收入" and row["数值"] == "100.00" for row in result.output_rows))

    def test_rejects_empty_source(self) -> None:
        with self.assertRaises(ValueError):
            anta_reporting.ReportSource(name="empty.xlsx", rows=[])


if __name__ == "__main__":
    unittest.main()
