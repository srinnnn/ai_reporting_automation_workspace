from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from ..domain import ProcessingResult, ValidationError, parse_non_negative_decimal, parse_non_negative_int, require_text


MODULE_KEY = "bosch_sms"
REQUIRED_FIELDS = (
    "品牌",
    "发送日期",
    "活动名称",
    "渠道",
    "发送量",
    "到达量",
    "点击量",
    "订单量",
    "成交金额",
)


def process(rows: list[dict[str, str]]) -> ProcessingResult:
    if not isinstance(rows, list):
        raise TypeError("rows must be list")
    output_rows: list[dict[str, str]] = []
    warnings: list[str] = []
    total_send = 0
    total_delivered = 0
    total_click = 0
    total_order = 0
    total_revenue = Decimal("0")

    for index, row in enumerate(rows, start=2):
        if not isinstance(row, dict):
            raise TypeError("each row must be dict")
        parsed = _parse_row(row, index)
        send_count = parsed["发送量"]
        delivered_count = parsed["到达量"]
        click_count = parsed["点击量"]
        order_count = parsed["订单量"]
        revenue = parsed["成交金额"]
        if delivered_count > send_count:
            warnings.append(f"第{index}行到达量大于发送量，请业务复核")
        if click_count > delivered_count:
            warnings.append(f"第{index}行点击量大于到达量，请业务复核")
        if order_count > click_count:
            warnings.append(f"第{index}行订单量大于点击量，请业务复核")

        total_send += send_count
        total_delivered += delivered_count
        total_click += click_count
        total_order += order_count
        total_revenue += revenue
        output_rows.append(
            {
                "品牌": parsed["品牌"],
                "发送日期": parsed["发送日期"],
                "活动名称": parsed["活动名称"],
                "渠道": parsed["渠道"],
                "发送量": str(send_count),
                "到达量": str(delivered_count),
                "点击量": str(click_count),
                "订单量": str(order_count),
                "成交金额": _format_decimal(revenue),
                "到达率": _rate(delivered_count, send_count),
                "点击率": _rate(click_count, delivered_count),
                "转化率": _rate(order_count, click_count),
                "单次发送产出": _money_rate(revenue, send_count),
            }
        )

    summary = {
        "总发送量": str(total_send),
        "总到达量": str(total_delivered),
        "总点击量": str(total_click),
        "总订单量": str(total_order),
        "总成交金额": _format_decimal(total_revenue),
        "整体到达率": _rate(total_delivered, total_send),
        "整体点击率": _rate(total_click, total_delivered),
        "整体转化率": _rate(total_order, total_click),
    }
    result = ProcessingResult(module=MODULE_KEY, output_rows=output_rows, summary=summary, warnings=warnings)
    assert result.output_rows
    return result


def _parse_row(row: dict[str, str], index: int) -> dict[str, object]:
    return {
        "品牌": require_text(row.get("品牌"), f"第{index}行品牌"),
        "发送日期": require_text(row.get("发送日期"), f"第{index}行发送日期"),
        "活动名称": require_text(row.get("活动名称"), f"第{index}行活动名称"),
        "渠道": require_text(row.get("渠道"), f"第{index}行渠道"),
        "发送量": parse_non_negative_int(row.get("发送量"), f"第{index}行发送量"),
        "到达量": parse_non_negative_int(row.get("到达量"), f"第{index}行到达量"),
        "点击量": parse_non_negative_int(row.get("点击量"), f"第{index}行点击量"),
        "订单量": parse_non_negative_int(row.get("订单量"), f"第{index}行订单量"),
        "成交金额": parse_non_negative_decimal(row.get("成交金额"), f"第{index}行成交金额"),
    }


def _rate(numerator: int, denominator: int) -> str:
    if denominator == 0:
        return "0.00%"
    value = (Decimal(numerator) / Decimal(denominator) * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"{value}%"


def _money_rate(numerator: Decimal, denominator: int) -> str:
    if denominator == 0:
        return "0.00"
    value = (numerator / Decimal(denominator)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return _format_decimal(value)


def _format_decimal(value: Decimal) -> str:
    return str(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

