from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from ..domain import ProcessingResult, ValidationError


MODULE_KEY = "anta_reporting"
WEEKLY_REQUIRED_FIELDS = (
    "美团周数据：订单状态、订单编号、商品名称、商品销售数量、商品实付销售额",
    "京东周数据：商品名称、实付销售额、商品销量",
)
MONTHLY_REQUIRED_FIELDS = (
    "美团月商品数据：订单状态、订单编号、商品名称、商品销售数量、商品实付销售额",
    "门店信息汇总：门店ID、营业状态、所在城市",
    "门店财务明细：收入、营业额、实付交易额、有效订单数、已取消订单数",
)


@dataclass(frozen=True)
class ReportSource:
    name: str
    rows: list[dict[str, str]]

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("name must be non-empty str")
        if not isinstance(self.rows, list):
            raise TypeError("rows must be list[dict[str, str]]")
        if not self.rows:
            raise ValidationError(f"{self.name}没有可处理数据")


def build_weekly_report(meituan_source: ReportSource, jd_source: ReportSource) -> ProcessingResult:
    _require_source(meituan_source, "meituan_source")
    _require_source(jd_source, "jd_source")
    logging.info("building anta weekly report")
    meituan_rows = _completed_rows(meituan_source.rows)
    jd_rows = jd_source.rows
    if not meituan_rows:
        raise ValidationError("美团周数据没有订单完成记录")
    output_rows: list[dict[str, str]] = []
    output_rows.extend(_summary_rows("周报", "美团", _sales_metrics(meituan_rows, "商品实付销售额", "商品销售数量", "订单编号")))
    output_rows.extend(_summary_rows("周报", "京东", _sales_metrics(jd_rows, "实付销售额", "商品销量", "")))
    output_rows.extend(_top_product_rows("周报", "美团", meituan_rows, "商品名称", "商品实付销售额", "商品销售数量"))
    output_rows.extend(_top_product_rows("周报", "京东", jd_rows, "商品名称", "实付销售额", "商品销量"))
    result = ProcessingResult(
        module=MODULE_KEY,
        output_rows=output_rows,
        summary={
            "报表类型": "安踏周报初稿",
            "美团完成订单行": str(len(meituan_rows)),
            "京东数据行": str(len(jd_rows)),
            "输出行数": str(len(output_rows)),
        },
        warnings=_report_warnings(output_rows),
    )
    assert result.output_rows
    return result


def build_monthly_report(product_source: ReportSource, store_source: ReportSource, finance_source: ReportSource) -> ProcessingResult:
    _require_source(product_source, "product_source")
    _require_source(store_source, "store_source")
    _require_source(finance_source, "finance_source")
    logging.info("building anta monthly report")
    completed_product_rows = _completed_rows(product_source.rows)
    if not completed_product_rows:
        raise ValidationError("美团月商品数据没有订单完成记录")
    output_rows: list[dict[str, str]] = []
    output_rows.extend(_summary_rows("月报", "美团商品", _sales_metrics(completed_product_rows, "商品实付销售额", "商品销售数量", "订单编号")))
    output_rows.extend(_summary_rows("月报", "门店", _store_metrics(store_source.rows)))
    output_rows.extend(_summary_rows("月报", "财务", _finance_metrics(finance_source.rows)))
    output_rows.extend(_top_product_rows("月报", "美团商品", completed_product_rows, "商品名称", "商品实付销售额", "商品销售数量"))
    result = ProcessingResult(
        module=MODULE_KEY,
        output_rows=output_rows,
        summary={
            "报表类型": "安踏月报初稿",
            "美团完成订单行": str(len(completed_product_rows)),
            "门店资料行": str(len(store_source.rows)),
            "财务资料行": str(len(finance_source.rows)),
            "输出行数": str(len(output_rows)),
        },
        warnings=_report_warnings(output_rows),
    )
    assert result.output_rows
    return result


def _sales_metrics(rows: list[dict[str, str]], amount_field: str, quantity_field: str, order_field: str) -> dict[str, str]:
    _require_rows(rows, "rows")
    amount = sum((_decimal(row.get(amount_field, "0"), amount_field) for row in rows), Decimal("0"))
    quantity = sum((_decimal(row.get(quantity_field, "0"), quantity_field) for row in rows), Decimal("0"))
    order_count = len({str(row.get(order_field, "")).strip() for row in rows if str(row.get(order_field, "")).strip()}) if order_field else len(rows)
    average_order = amount / Decimal(order_count) if order_count > 0 else Decimal("0")
    return {
        "销售额": _money(amount),
        "销量": _number(quantity),
        "订单数": str(order_count),
        "客单价": _money(average_order),
    }


def _store_metrics(rows: list[dict[str, str]]) -> dict[str, str]:
    _require_rows(rows, "rows")
    store_ids = {str(row.get("门店ID", "")).strip() or str(row.get("门店编号", "")).strip() for row in rows}
    active_rows = [row for row in rows if "营业" in str(row.get("营业状态", ""))]
    cities = {str(row.get("所在城市", "")).strip() or str(row.get("城市", "")).strip() for row in rows if str(row.get("所在城市", "")).strip() or str(row.get("城市", "")).strip()}
    return {
        "门店数": str(len({store_id for store_id in store_ids if store_id})),
        "营业门店数": str(len(active_rows)),
        "覆盖城市数": str(len(cities)),
    }


def _finance_metrics(rows: list[dict[str, str]]) -> dict[str, str]:
    _require_rows(rows, "rows")
    income = sum((_decimal(row.get("收入", "0"), "收入") for row in rows), Decimal("0"))
    turnover = sum((_decimal(row.get("营业额", "0"), "营业额") for row in rows), Decimal("0"))
    paid_amount = sum((_decimal(row.get("实付交易额", "0"), "实付交易额") for row in rows), Decimal("0"))
    valid_orders = sum((_decimal(row.get("有效订单数", "0"), "有效订单数") for row in rows), Decimal("0"))
    cancelled_orders = sum((_decimal(row.get("已取消订单数", "0"), "已取消订单数") for row in rows), Decimal("0"))
    return {
        "收入": _money(income),
        "营业额": _money(turnover),
        "实付交易额": _money(paid_amount),
        "有效订单数": _number(valid_orders),
        "已取消订单数": _number(cancelled_orders),
    }


def _summary_rows(report_type: str, platform: str, metrics: dict[str, str]) -> list[dict[str, str]]:
    if not metrics:
        raise ValueError("metrics must not be empty")
    return [
        {
            "报表类型": report_type,
            "模块": "核心指标",
            "平台": platform,
            "指标": key,
            "数值": value,
            "说明": "系统按已归档原始数据自动汇总",
        }
        for key, value in metrics.items()
    ]


def _top_product_rows(report_type: str, platform: str, rows: list[dict[str, str]], name_field: str, amount_field: str, quantity_field: str) -> list[dict[str, str]]:
    _require_rows(rows, "rows")
    grouped: dict[str, dict[str, Decimal]] = {}
    for row in rows:
        product_name = str(row.get(name_field, "")).strip() or "未命名商品"
        item = grouped.setdefault(product_name, {"amount": Decimal("0"), "quantity": Decimal("0")})
        item["amount"] += _decimal(row.get(amount_field, "0"), amount_field)
        item["quantity"] += _decimal(row.get(quantity_field, "0"), quantity_field)
    sorted_items = sorted(grouped.items(), key=lambda item: item[1]["amount"], reverse=True)[:10]
    return [
        {
            "报表类型": report_type,
            "模块": "TOP商品",
            "平台": platform,
            "指标": product_name,
            "数值": _money(values["amount"]),
            "说明": f"销量：{_number(values['quantity'])}",
        }
        for product_name, values in sorted_items
    ]


def _completed_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    _require_rows(rows, "rows")
    filtered = [row for row in rows if "完成" in str(row.get("订单状态", ""))]
    return filtered if filtered else rows


def _report_warnings(rows: list[dict[str, str]]) -> list[str]:
    _require_rows(rows, "rows")
    warnings: list[str] = ["当前为数据初稿，生成 PPT/Excel 成品前仍需人工确认结论文案。"]
    if any(row["指标"] == "未命名商品" for row in rows):
        warnings.append("存在未命名商品，请检查源表商品名称字段。")
    return warnings


def _decimal(value: object, field_name: str) -> Decimal:
    if not isinstance(field_name, str) or not field_name.strip():
        raise ValueError("field_name must not be empty")
    text = "" if value is None else str(value).strip().replace(",", "").replace("\t", "")
    if text in ("", "-", "--"):
        return Decimal("0")
    if text.endswith("%"):
        text = text[:-1]
    try:
        return Decimal(text)
    except InvalidOperation as exc:
        raise ValidationError(f"{field_name}必须是数字，当前值：{value}") from exc


def _money(value: Decimal) -> str:
    if not isinstance(value, Decimal):
        raise TypeError("value must be Decimal")
    return str(value.quantize(Decimal("0.01")))


def _number(value: Decimal) -> str:
    if not isinstance(value, Decimal):
        raise TypeError("value must be Decimal")
    if value == value.to_integral_value():
        return str(value.to_integral_value())
    return str(value.quantize(Decimal("0.01")))


def _require_source(source: ReportSource, field_name: str) -> None:
    if not isinstance(source, ReportSource):
        raise TypeError(f"{field_name} must be ReportSource")


def _require_rows(rows: list[dict[str, str]], field_name: str) -> None:
    if not isinstance(rows, list):
        raise TypeError(f"{field_name} must be list[dict[str, str]]")
    if not rows:
        raise ValidationError(f"{field_name}不能为空")
