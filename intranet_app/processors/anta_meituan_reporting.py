from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from ..domain import ProcessingResult, ValidationError


MODULE_KEY = "anta_meituan_reporting"
REQUIRED_PRODUCT_FIELDS = (
    "日期",
    "订单编号",
    "店铺名称",
    "店铺ID",
    "店铺所在城市",
    "订单状态",
    "商品分类",
    "商品名称",
    "商品销售数量",
    "商品实付销售额",
)
REQUIRED_FINANCE_FIELDS = (
    "开始时间",
    "结束时间",
    "商家ID",
    "商家名称",
    "省份",
    "城市",
    "实付交易额",
    "有效订单数",
)
REQUIRED_TRAFFIC_FIELDS = (
    "开始时间",
    "结束时间",
    "商家ID",
    "商家名称",
    "城市",
    "曝光人数",
    "入店人数",
    "下单人数",
    "入店转化率",
    "下单转化率",
)
REQUIRED_REVIEW_FIELDS = (
    "评价提交日期",
    "店铺名称",
    "店铺ID",
    "店铺所在城市",
    "订单商品",
    "用户评价",
    "商家评分",
    "配送体验评分",
)


@dataclass(frozen=True)
class MeituanReportSources:
    product_rows: list[dict[str, str]]
    finance_rows: list[dict[str, str]]
    traffic_rows: list[dict[str, str]]
    review_rows: list[dict[str, str]]

    def __post_init__(self) -> None:
        _require_rows(self.product_rows, "product_rows")
        if not isinstance(self.finance_rows, list):
            raise TypeError("finance_rows must be list")
        if not isinstance(self.traffic_rows, list):
            raise TypeError("traffic_rows must be list")
        if not isinstance(self.review_rows, list):
            raise TypeError("review_rows must be list")


@dataclass(frozen=True)
class ReportWindow:
    report_type: str
    start_date: str
    end_date: str

    def __post_init__(self) -> None:
        if self.report_type not in {"daily", "weekly"}:
            raise ValidationError("report_type must be daily or weekly")
        _parse_compact_date(self.start_date, "start_date")
        _parse_compact_date(self.end_date, "end_date")
        if self.start_date > self.end_date:
            raise ValidationError("start_date must not be later than end_date")


def build_meituan_daily_report(sources: MeituanReportSources, report_date: str) -> ProcessingResult:
    if not isinstance(sources, MeituanReportSources):
        raise TypeError("sources must be MeituanReportSources")
    _parse_compact_date(report_date, "report_date")
    logging.info("building Anta Meituan daily report: %s", report_date)
    return _build_report(sources, ReportWindow("daily", report_date, report_date))


def build_meituan_weekly_report(sources: MeituanReportSources, start_date: str, end_date: str) -> ProcessingResult:
    if not isinstance(sources, MeituanReportSources):
        raise TypeError("sources must be MeituanReportSources")
    logging.info("building Anta Meituan weekly report: %s-%s", start_date, end_date)
    return _build_report(sources, ReportWindow("weekly", start_date, end_date))


def _build_report(sources: MeituanReportSources, window: ReportWindow) -> ProcessingResult:
    if not isinstance(sources, MeituanReportSources):
        raise TypeError("sources must be MeituanReportSources")
    if not isinstance(window, ReportWindow):
        raise TypeError("window must be ReportWindow")
    _validate_headers(sources.product_rows, REQUIRED_PRODUCT_FIELDS, "商品/订单数据")
    finance_source_rows = _finance_rows_with_unit_price(sources.finance_rows)
    if finance_source_rows:
        _validate_headers(finance_source_rows, REQUIRED_FINANCE_FIELDS, "门店财务数据")
    if sources.traffic_rows:
        _validate_headers(sources.traffic_rows, REQUIRED_TRAFFIC_FIELDS, "门店流量数据")
    if sources.review_rows:
        _validate_headers(sources.review_rows, REQUIRED_REVIEW_FIELDS, "服务评价数据")

    product_rows = _filter_rows_by_window(sources.product_rows, "日期", window)
    finance_rows = _filter_rows_by_window(finance_source_rows, "开始时间", window)
    traffic_rows = _filter_rows_by_window(sources.traffic_rows, "开始时间", window)
    review_rows = (
        []
        if window.report_type == "daily"
        else _filter_rows_by_window(sources.review_rows, "评价提交日期", window) if sources.review_rows else []
    )
    completed_product_rows = _completed_product_rows(product_rows)
    if not completed_product_rows:
        raise ValidationError("商品/订单数据在当前日期范围内没有可用完成订单")

    sales_amount = sum((_money_value(row.get("商品实付销售额", ""), "商品实付销售额") for row in completed_product_rows), Decimal("0"))
    sales_quantity = sum((_money_value(row.get("商品销售数量", ""), "商品销售数量") for row in completed_product_rows), Decimal("0"))
    order_count = len({row["订单编号"].strip() for row in completed_product_rows if row.get("订单编号", "").strip()})
    finance_paid_amount = sum((_money_value(row.get("实付交易额", ""), "实付交易额") for row in finance_rows), Decimal("0"))
    finance_order_count = sum((_money_value(row.get("有效订单数", ""), "有效订单数") for row in finance_rows), Decimal("0"))
    customer_unit_price = sales_amount / Decimal(order_count) if order_count > 0 else Decimal("0")
    ranking_window = _ranking_window(window)
    ranking_product_rows = _completed_product_rows(_filter_rows_by_window(sources.product_rows, "日期", ranking_window))
    ranking_finance_rows = [] if window.report_type == "daily" else finance_rows
    store_top = _top_stores(ranking_finance_rows, ranking_product_rows)
    product_top = _top_products(ranking_product_rows)
    traffic_summary = _traffic_summary(traffic_rows)
    review_summary = _review_summary(review_rows)
    warnings = _report_warnings(window, product_rows, finance_rows, traffic_rows, review_rows)

    label = "日报" if window.report_type == "daily" else "周报"
    title = f"ANTA KIDS {window.end_date} 美团即时零售销售{label}"
    rows: list[dict[str, str]] = []
    rows.extend(_copy_rows(title, window, sales_amount, order_count, store_top, product_top, warnings))
    rows.extend(
        _metric_rows(
            label,
            "核心指标",
            (
                ("销售额", _format_money(sales_amount), "按商品实付销售额汇总完成订单"),
                ("销量", _format_number(sales_quantity), "按商品销售数量汇总完成订单"),
                ("订单数", str(order_count), "按订单编号去重"),
                ("客单价", _format_money(customer_unit_price), "销售额 / 订单数"),
                ("财务实付交易额", _format_money(finance_paid_amount), "门店财务明细口径，用于和商品口径对账"),
                ("财务有效订单数", _format_number(finance_order_count), "门店财务明细口径"),
            ),
        )
    )
    rows.extend(_rank_rows(label, "近7天TOP门店" if window.report_type == "daily" else "本周TOP门店", store_top, "门店"))
    rows.extend(_rank_rows(label, "近7天TOP商品" if window.report_type == "daily" else "本周TOP商品", product_top, "商品"))
    rows.extend(_metric_rows(label, "流量转化", traffic_summary))
    if window.report_type != "daily":
        rows.extend(_metric_rows(label, "评价服务", review_summary))
        rows.extend(_weekly_selection_rows(completed_product_rows))
        rows.extend(_weekly_copy_direction_rows(product_top))
    rows.extend(_warning_rows(label, warnings))
    summary = {
        "报表类型": f"安踏美团{label}",
        "品牌": "安踏儿童",
        "平台": "美团",
        "渠道": "即时零售",
        "开始日期": window.start_date,
        "结束日期": window.end_date,
        "销售额": _format_money(sales_amount),
        "订单数": str(order_count),
        "输出行数": str(len(rows)),
    }
    result = ProcessingResult(module=MODULE_KEY, output_rows=rows, summary=summary, warnings=warnings)
    assert result.output_rows
    return result


def _copy_rows(
    title: str,
    window: ReportWindow,
    sales_amount: Decimal,
    order_count: int,
    store_top: list[tuple[str, Decimal, str]],
    product_top: list[tuple[str, Decimal, str]],
    warnings: list[str],
) -> list[dict[str, str]]:
    if not isinstance(title, str) or not title.strip():
        raise ValueError("title must not be empty")
    top_store_text = "、".join(item[0] for item in store_top[:5]) if store_top else "暂无门店榜单"
    top_product = product_top[0][0] if product_top else "暂无商品榜单"
    data_note = "；".join(warnings) if warnings else "数据完整"
    body = (
        f"📌 截止 {window.end_date} 安踏儿童美团即时零售销售快报\n"
        f"1.【销售】销售额 {_format_money(sales_amount)}，有效订单 {order_count} 单。\n"
        f"2.【门店TOP】{top_store_text} 等门店表现靠前。\n"
        f"3.【商品TOP】{top_product} 当前贡献领先，建议同步关注库存与活动承接。\n"
        f"4.【数据状态】{data_note}"
    )
    return [
        _row(window, "快报文案", "标题", title, "可直接用于业务群日报/周报标题"),
        _row(window, "快报文案", "正文", body, "AI不编造事实，全部数字来自美团导出数据"),
    ]


def _metric_rows(report_label: str, section: str, metrics: tuple[tuple[str, str, str], ...]) -> list[dict[str, str]]:
    if not isinstance(report_label, str) or not report_label.strip():
        raise ValueError("report_label must not be empty")
    if not isinstance(section, str) or not section.strip():
        raise ValueError("section must not be empty")
    if not metrics:
        raise ValueError("metrics must not be empty")
    return [
        {
            "报表类型": report_label,
            "板块": section,
            "排序": str(index),
            "名称": name,
            "数值": value,
            "说明": note,
        }
        for index, (name, value, note) in enumerate(metrics, start=1)
    ]


def _rank_rows(report_label: str, section: str, items: list[tuple[str, Decimal, str]], name_label: str) -> list[dict[str, str]]:
    if not isinstance(items, list):
        raise TypeError("items must be list")
    if not items:
        return [
            {
                "报表类型": report_label,
                "板块": section,
                "排序": "1",
                "名称": f"暂无{name_label}数据",
                "数值": "0.00",
                "说明": "源数据为空或当前日期范围内无有效记录",
            }
        ]
    return [
        {
            "报表类型": report_label,
            "板块": section,
            "排序": str(index),
            "名称": name,
            "数值": _format_money(amount),
            "说明": note,
        }
        for index, (name, amount, note) in enumerate(items[:10], start=1)
    ]


def _weekly_selection_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    if not isinstance(rows, list) or not rows:
        raise ValidationError("weekly selection rows must not be empty")
    grouped: dict[str, dict[str, Decimal | str | set[str]]] = {}
    for row in rows:
        product_name = row.get("商品名称", "").strip() or "未命名商品"
        sku_code = row.get("商品SKU码", "").strip() or row.get("UPC码", "").strip()
        category = row.get("商品分类", "").strip() or "未分类"
        item = grouped.setdefault(
            product_name,
            {
                "sku": sku_code,
                "category": category,
                "quantity": Decimal("0"),
                "amount": Decimal("0"),
                "orders": set(),
            },
        )
        item["quantity"] = item["quantity"] + _money_value(row.get("商品销售数量", ""), "商品销售数量")
        item["amount"] = item["amount"] + _money_value(row.get("商品实付销售额", ""), "商品实付销售额")
        order_id = row.get("订单编号", "").strip()
        if order_id:
            item["orders"].add(order_id)
    ranked = sorted(
        grouped.items(),
        key=lambda pair: (pair[1]["amount"], pair[1]["quantity"], Decimal(len(pair[1]["orders"]))),
        reverse=True,
    )
    output_rows: list[dict[str, str]] = []
    for index, (product_name, item) in enumerate(ranked[:5], start=1):
        quantity = item["quantity"]
        amount = item["amount"]
        order_count = len(item["orders"])
        if not isinstance(quantity, Decimal) or not isinstance(amount, Decimal):
            raise TypeError("selection metrics must be Decimal")
        recommendation = _weekly_selection_recommendation(index, amount, quantity)
        output_rows.append(
            {
                "报表类型": "周报",
                "板块": "下周选品建议",
                "排序": str(index),
                "名称": product_name,
                "数值": recommendation,
                "说明": (
                    f"本周销售额{_format_money(amount)}；销量{_format_number(quantity)}；订单{order_count}；"
                    f"SKU/UPC：{item['sku'] or '缺失'}；类目：{item['category'] or '缺失'}"
                ),
            }
        )
    assert output_rows
    return output_rows


def _weekly_selection_recommendation(index: int, amount: Decimal, quantity: Decimal) -> str:
    if not isinstance(index, int) or index <= 0:
        raise ValueError("index must be positive")
    if not isinstance(amount, Decimal) or not isinstance(quantity, Decimal):
        raise TypeError("amount and quantity must be Decimal")
    if index <= 3 and amount > Decimal("0"):
        return "建议进入下周重点主推池"
    if quantity > Decimal("0"):
        return "建议作为补充推荐款，结合库存和活动资源复核"
    return "暂不主推，仅保留观察"


def _weekly_copy_direction_rows(product_top: list[tuple[str, Decimal, str]]) -> list[dict[str, str]]:
    if not isinstance(product_top, list):
        raise TypeError("product_top must be list")
    if not product_top:
        return [
            {
                "报表类型": "周报",
                "板块": "内容文案建议",
                "排序": "1",
                "名称": "待补充",
                "数值": "当前周报缺少可用于内容建议的商品榜单。",
                "说明": "需先补齐商品订单数据",
            }
        ]
    output_rows: list[dict[str, str]] = []
    for index, (product_name, amount, note) in enumerate(product_top[:3], start=1):
        body = (
            f"本周{product_name}在美团即时零售表现靠前，可作为下周内容重点。"
            "文案建议围绕商品名称、类目场景和本周销售表现表达，价格、优惠、库存和材质卖点需业务补充后再发布。"
        )
        output_rows.append(
            {
                "报表类型": "周报",
                "板块": "内容文案建议",
                "排序": str(index),
                "名称": product_name,
                "数值": body,
                "说明": f"本周销售额{_format_money(amount)}；{note}；AI不编造未提供卖点",
            }
        )
    assert output_rows
    return output_rows


def _warning_rows(report_label: str, warnings: list[str]) -> list[dict[str, str]]:
    if not isinstance(warnings, list):
        raise TypeError("warnings must be list")
    if not warnings:
        warnings = ["数据完整，未发现阻断项。"]
    return [
        {
            "报表类型": report_label,
            "板块": "数据质量",
            "排序": str(index),
            "名称": "提示",
            "数值": warning,
            "说明": "需要业务确认或后续补数据的事项",
        }
        for index, warning in enumerate(warnings, start=1)
    ]


def _row(window: ReportWindow, section: str, name: str, value: str, note: str) -> dict[str, str]:
    return {
        "报表类型": "日报" if window.report_type == "daily" else "周报",
        "板块": section,
        "排序": "0",
        "名称": name,
        "数值": value,
        "说明": note,
    }


def _top_stores(finance_rows: list[dict[str, str]], product_rows: list[dict[str, str]]) -> list[tuple[str, Decimal, str]]:
    grouped: dict[str, dict[str, object]] = {}
    if finance_rows:
        for row in finance_rows:
            store_id = row.get("商家ID", "").strip()
            store_name = row.get("商家名称", "").strip() or store_id or "未命名门店"
            city = row.get("城市", "").strip()
            key = store_id or store_name
            item = grouped.setdefault(key, {"name": store_name, "amount": Decimal("0"), "orders": Decimal("0"), "city": city})
            item["amount"] = item["amount"] + _money_value(row.get("实付交易额", ""), "实付交易额")
            item["orders"] = item["orders"] + _money_value(row.get("有效订单数", ""), "有效订单数")
            if city:
                item["city"] = city
    else:
        for row in product_rows:
            store_id = row.get("店铺ID", "").strip()
            store_name = row.get("店铺名称", "").strip() or store_id or "未命名门店"
            city = row.get("店铺所在城市", "").strip()
            key = store_id or store_name
            item = grouped.setdefault(key, {"name": store_name, "amount": Decimal("0"), "orders": set(), "city": city})
            item["amount"] = item["amount"] + _money_value(row.get("商品实付销售额", ""), "商品实付销售额")
            item["orders"].add(row.get("订单编号", "").strip())
            if city:
                item["city"] = city
    result: list[tuple[str, Decimal, str]] = []
    for item in grouped.values():
        order_value = item["orders"]
        order_text = str(len(order_value)) if isinstance(order_value, set) else _format_number(order_value)
        city_text = str(item["city"]).strip()
        note = f"城市：{city_text or '未知'}；有效订单：{order_text}"
        result.append((str(item["name"]), item["amount"], note))
    return sorted(result, key=lambda item: item[1], reverse=True)[:10]


def _top_products(rows: list[dict[str, str]]) -> list[tuple[str, Decimal, str]]:
    grouped: dict[str, dict[str, Decimal | str]] = {}
    for row in rows:
        product_name = row.get("商品名称", "").strip() or "未命名商品"
        sku_code = row.get("商品SKU码", "").strip() or row.get("UPC码", "").strip()
        category = row.get("商品分类", "").strip()
        item = grouped.setdefault(product_name, {"amount": Decimal("0"), "quantity": Decimal("0"), "sku": sku_code, "category": category})
        item["amount"] = item["amount"] + _money_value(row.get("商品实付销售额", ""), "商品实付销售额")
        item["quantity"] = item["quantity"] + _money_value(row.get("商品销售数量", ""), "商品销售数量")
    result = [
        (
            product_name,
            item["amount"],
            f"销量：{_format_number(item['quantity'])}；SKU/UPC：{item['sku'] or '缺失'}；分类：{item['category'] or '缺失'}",
        )
        for product_name, item in grouped.items()
    ]
    return sorted(result, key=lambda item: item[1], reverse=True)[:10]


def _traffic_summary(rows: list[dict[str, str]]) -> tuple[tuple[str, str, str], ...]:
    exposure = sum((_money_value(row.get("曝光人数", ""), "曝光人数") for row in rows), Decimal("0"))
    visits = sum((_money_value(row.get("入店人数", ""), "入店人数") for row in rows), Decimal("0"))
    order_users = sum((_money_value(row.get("下单人数", ""), "下单人数") for row in rows), Decimal("0"))
    visit_rate = visits / exposure * Decimal("100") if exposure > 0 else Decimal("0")
    order_rate = order_users / visits * Decimal("100") if visits > 0 else Decimal("0")
    return (
        ("曝光人数", _format_number(exposure), "门店流量明细汇总"),
        ("入店人数", _format_number(visits), "门店流量明细汇总"),
        ("下单人数", _format_number(order_users), "门店流量明细汇总"),
        ("入店转化率", f"{_format_percent(visit_rate)}%", "入店人数 / 曝光人数"),
        ("下单转化率", f"{_format_percent(order_rate)}%", "下单人数 / 入店人数"),
    )


def _review_summary(rows: list[dict[str, str]]) -> tuple[tuple[str, str, str], ...]:
    if not rows:
        return (
            ("评价数", "0", "当前周期未提供评价数据"),
            ("平均商家评分", "缺失", "需服务评价数据"),
            ("平均配送体验评分", "缺失", "需服务评价数据"),
        )
    merchant_scores = [_money_value(row.get("商家评分", ""), "商家评分") for row in rows if row.get("商家评分", "").strip()]
    delivery_scores = [_money_value(row.get("配送体验评分", ""), "配送体验评分") for row in rows if row.get("配送体验评分", "").strip()]
    avg_merchant = sum(merchant_scores, Decimal("0")) / Decimal(len(merchant_scores)) if merchant_scores else Decimal("0")
    avg_delivery = sum(delivery_scores, Decimal("0")) / Decimal(len(delivery_scores)) if delivery_scores else Decimal("0")
    negative_rows = [row for row in rows if _money_value(row.get("商家评分", "5"), "商家评分") < Decimal("4")]
    return (
        ("评价数", str(len(rows)), "服务评价数据行数"),
        ("平均商家评分", _format_number(avg_merchant), "按商家评分均值计算"),
        ("平均配送体验评分", _format_number(avg_delivery), "按配送体验评分均值计算"),
        ("低分评价数", str(len(negative_rows)), "商家评分低于4分"),
    )


def _report_warnings(
    window: ReportWindow,
    product_rows: list[dict[str, str]],
    finance_rows: list[dict[str, str]],
    traffic_rows: list[dict[str, str]],
    review_rows: list[dict[str, str]],
) -> list[str]:
    warnings: list[str] = []
    if not finance_rows:
        warnings.append("门店财务数据缺失，门店TOP将退回商品订单口径。")
    if not traffic_rows:
        warnings.append("门店流量数据缺失，无法生成流量转化板块。")
    if window.report_type != "daily" and not review_rows:
        warnings.append("服务评价数据缺失，无法生成评价服务板块。")
    actual_dates = sorted({date_value for row in product_rows for date_value in _compact_dates_from_text(row.get("日期", ""))})
    coverage_days = _covered_day_count(actual_dates)
    if window.report_type == "daily" and coverage_days < 7:
        warnings.append(f"日报近7天榜单当前仅覆盖 {coverage_days} 天，需连续入库满7天后完整展示。")
    if window.report_type == "weekly" and coverage_days < 7:
        warnings.append(f"周报商品数据当前覆盖 {coverage_days} 天，未满7天时仅输出阶段性周报。")
    review_dates = sorted(
        {
            _compact_date_from_text(row.get("评价提交日期", ""))
            for row in review_rows
            if _compact_date_from_text(row.get("评价提交日期", ""))
        }
    )
    if window.report_type != "daily" and review_dates and review_dates[-1] < window.end_date:
        warnings.append(f"评价数据仅覆盖到 {review_dates[-1]}，未覆盖报表结束日 {window.end_date}。")
    return warnings


def _filter_rows_by_window(rows: list[dict[str, str]], field_name: str, window: ReportWindow) -> list[dict[str, str]]:
    if not rows:
        return []
    result: list[dict[str, str]] = []
    for row in rows:
        row_dates = _row_dates(row, field_name, window)
        if not row_dates:
            continue
        if any(window.start_date <= row_date <= window.end_date for row_date in row_dates):
            result.append(row)
    logging.info("filtered %s rows to %s rows for %s-%s", len(rows), len(result), window.start_date, window.end_date)
    return result


def _row_dates(row: dict[str, str], field_name: str, window: ReportWindow) -> list[str]:
    if not isinstance(row, dict):
        raise TypeError("row must be dict")
    dates = _compact_dates_from_text(row.get(field_name, ""))
    if field_name == "日期" and len(dates) > 1 and row.get("下单时间", "").strip():
        return _compact_dates_from_text(row.get("下单时间", ""))
    if window.report_type == "daily" and field_name == "开始时间" and len(dates) == 1:
        end_dates = _compact_dates_from_text(row.get("结束时间", ""))
        if end_dates and end_dates[-1] != dates[0]:
            return []
    return dates


def _ranking_window(window: ReportWindow) -> ReportWindow:
    if not isinstance(window, ReportWindow):
        raise TypeError("window must be ReportWindow")
    if window.report_type == "weekly":
        return window
    end = _parse_compact_date(window.end_date, "end_date")
    start = end - timedelta(days=6)
    result = ReportWindow("weekly", start.strftime("%Y%m%d"), window.end_date)
    assert result.start_date <= result.end_date
    return result


def _completed_product_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    result = [row for row in rows if "完成" in row.get("订单状态", "")]
    return result if result else rows


def _validate_headers(rows: list[dict[str, str]], required_fields: tuple[str, ...], source_name: str) -> None:
    _require_rows(rows, source_name)
    headers = set(rows[0].keys())
    missing = tuple(field for field in required_fields if field not in headers)
    if missing:
        raise ValidationError(f"{source_name}缺少字段：{', '.join(missing)}")


def _finance_rows_with_unit_price(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    if not isinstance(rows, list):
        raise TypeError("rows must be list[dict[str, str]]")
    result: list[dict[str, str]] = []
    for row in rows:
        if not isinstance(row, dict):
            raise TypeError("finance row must be dict")
        normalized = dict(row)
        if not normalized.get("实付单均价", "").strip():
            paid_amount = _money_value(normalized.get("实付交易额", ""), "实付交易额")
            order_count = _money_value(normalized.get("有效订单数", ""), "有效订单数")
            normalized["实付单均价"] = _format_money(paid_amount / order_count) if order_count > 0 else "0.00"
        result.append(normalized)
    assert len(result) == len(rows)
    return result


def _compact_date_from_text(value: object) -> str:
    dates = _compact_dates_from_text(value)
    return dates[0] if dates else ""


def _compact_dates_from_text(value: object) -> list[str]:
    text = "" if value is None else str(value).strip()
    digits = "".join(ch for ch in text if ch.isdigit())
    if len(digits) < 8:
        return []
    return [digits[index : index + 8] for index in range(0, len(digits) - 7, 8)]


def _covered_day_count(date_values: list[str]) -> int:
    if not isinstance(date_values, list):
        raise TypeError("date_values must be list")
    if not date_values:
        return 0
    if len(date_values) >= 2:
        start = _parse_compact_date(date_values[0], "start_date")
        end = _parse_compact_date(date_values[-1], "end_date")
        return (end - start).days + 1
    return 1


def _parse_compact_date(value: object, field_name: str) -> date:
    text = _compact_date_from_text(value)
    if len(text) != 8:
        raise ValidationError(f"{field_name} must be YYYYMMDD")
    try:
        return date(int(text[:4]), int(text[4:6]), int(text[6:8]))
    except ValueError as exc:
        raise ValidationError(f"{field_name} must be a valid date") from exc


def _money_value(value: object, field_name: str) -> Decimal:
    if not isinstance(field_name, str) or not field_name.strip():
        raise ValueError("field_name must not be empty")
    text = "" if value is None else str(value).strip().replace(",", "").replace("\t", "")
    if text in {"", "-", "--"}:
        return Decimal("0")
    if text.endswith("%"):
        text = text[:-1]
    try:
        result = Decimal(text)
    except InvalidOperation as exc:
        raise ValidationError(f"{field_name}必须是数字，当前值：{value}") from exc
    assert isinstance(result, Decimal)
    return result


def _format_money(value: Decimal) -> str:
    if not isinstance(value, Decimal):
        raise TypeError("value must be Decimal")
    return str(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _format_number(value: Decimal | object) -> str:
    if not isinstance(value, Decimal):
        value = Decimal(str(value))
    if value == value.to_integral_value():
        return str(value.to_integral_value())
    return str(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _format_percent(value: Decimal) -> str:
    if not isinstance(value, Decimal):
        raise TypeError("value must be Decimal")
    return str(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _require_rows(rows: list[dict[str, str]], field_name: str) -> None:
    if not isinstance(rows, list):
        raise TypeError(f"{field_name} must be list[dict[str, str]]")
    if not rows:
        raise ValidationError(f"{field_name}不能为空")
