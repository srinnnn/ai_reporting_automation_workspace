from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from ..domain import ProcessingResult, ValidationError, parse_non_negative_decimal, parse_non_negative_int, require_text


MODULE_KEY = "ai_selection"
PROJECT_GENERIC = "通用选品"
PROJECT_ANTA = "安踏儿童"
PROJECT_OPTIONS = (PROJECT_GENERIC, PROJECT_ANTA)

GENERIC_REQUIRED_FIELDS = (
    "品牌",
    "平台",
    "商品ID",
    "商品名称",
    "类目",
    "售价",
    "近30天销量",
    "库存",
    "毛利率",
    "活动匹配度",
)
ANTA_REQUIRED_FIELDS = (
    "平台",
    "款号",
    "商品名称",
    "大类",
    "类目",
    "近7天销量",
    "近7天销售额",
    "近30天销量",
    "库存",
    "场景主题",
    "选品角色",
    "活动匹配度",
)
REQUIRED_FIELDS = (
    "项目（页面选择：通用选品/安踏儿童）",
    "通用选品字段：品牌、平台、商品ID、商品名称、类目、售价、近30天销量、库存、毛利率、活动匹配度",
    "安踏儿童字段：平台、款号、商品名称、大类、类目、近7天销量、近7天销售额、近30天销量、库存、场景主题、选品角色、活动匹配度",
)
ROLE_SCORES = {"核心推荐": Decimal("15"), "潜力拓展": Decimal("10"), "补充品类": Decimal("5")}


def process(rows: list[dict[str, str]]) -> ProcessingResult:
    if not isinstance(rows, list):
        raise TypeError("rows must be list")
    if not rows:
        raise ValidationError("选品数据不能为空")
    project = _resolve_project(rows[0])
    if project == PROJECT_ANTA:
        return _process_anta(rows)
    if project == PROJECT_GENERIC:
        return _process_generic(rows)
    raise ValidationError(f"项目只能选择：{', '.join(PROJECT_OPTIONS)}")


def _process_generic(rows: list[dict[str, str]]) -> ProcessingResult:
    output_rows: list[dict[str, str]] = []
    warnings: list[str] = []
    total_score = Decimal("0")
    high_priority_count = 0

    for index, row in enumerate(rows, start=2):
        brand = require_text(row.get("品牌"), f"第{index}行品牌")
        platform = require_text(row.get("平台"), f"第{index}行平台")
        product_id = require_text(row.get("商品ID"), f"第{index}行商品ID")
        product_name = require_text(row.get("商品名称"), f"第{index}行商品名称")
        category = require_text(row.get("类目"), f"第{index}行类目")
        price = parse_non_negative_decimal(row.get("售价"), f"第{index}行售价")
        sales = parse_non_negative_int(row.get("近30天销量"), f"第{index}行近30天销量")
        stock = parse_non_negative_int(row.get("库存"), f"第{index}行库存")
        gross_margin = parse_non_negative_decimal(row.get("毛利率"), f"第{index}行毛利率")
        if gross_margin > Decimal("100"):
            raise ValidationError(f"第{index}行毛利率不能大于100")
        activity_fit = _parse_activity_fit(row, index)
        score = _score_generic(sales, stock, gross_margin, activity_fit)
        priority = _priority(score)
        reason = _reason_generic(sales, stock, gross_margin, activity_fit)
        row_has_warning = False
        if stock < 20 and sales >= 50:
            warnings.append(f"第{index}行库存偏低但销量较高，请确认是否能参与主推")
            row_has_warning = True
        if gross_margin < Decimal("15"):
            warnings.append(f"第{index}行毛利率低于15%，不建议默认进入主推池")
            row_has_warning = True
        if priority == "高":
            high_priority_count += 1
        total_score += score
        output_rows.append(
            {
                "项目": PROJECT_GENERIC,
                "品牌": brand,
                "平台": platform,
                "商品ID": product_id,
                "商品名称": product_name,
                "类目": category,
                "售价": _format_decimal(price),
                "近30天销量": str(sales),
                "库存": str(stock),
                "毛利率": f"{_format_decimal(gross_margin)}%",
                "活动匹配度": str(activity_fit),
                "AI选品分": _format_decimal(score),
                "推荐优先级": priority,
                "推荐理由": reason,
                "人工复核": "需要" if row_has_warning else "建议复核",
            }
        )

    return _build_result(output_rows, total_score, high_priority_count, warnings)


def _process_anta(rows: list[dict[str, str]]) -> ProcessingResult:
    output_rows: list[dict[str, str]] = []
    warnings: list[str] = []
    total_score = Decimal("0")
    high_priority_count = 0

    for index, row in enumerate(rows, start=2):
        platform = require_text(row.get("平台"), f"第{index}行平台")
        product_code = require_text(row.get("款号"), f"第{index}行款号")
        product_name = require_text(row.get("商品名称"), f"第{index}行商品名称")
        major_category = require_text(row.get("大类"), f"第{index}行大类")
        category = require_text(row.get("类目"), f"第{index}行类目")
        weekly_sales = parse_non_negative_int(row.get("近7天销量"), f"第{index}行近7天销量")
        weekly_revenue = parse_non_negative_decimal(row.get("近7天销售额"), f"第{index}行近7天销售额")
        monthly_sales = parse_non_negative_int(row.get("近30天销量"), f"第{index}行近30天销量")
        stock = parse_non_negative_int(row.get("库存"), f"第{index}行库存")
        theme = require_text(row.get("场景主题"), f"第{index}行场景主题")
        role = require_text(row.get("选品角色"), f"第{index}行选品角色")
        if role not in ROLE_SCORES:
            raise ValidationError(f"第{index}行选品角色只能填写：核心推荐、潜力拓展、补充品类")
        activity_fit = _parse_activity_fit(row, index)
        score = _score_anta(weekly_sales, weekly_revenue, monthly_sales, stock, role, activity_fit)
        priority = _priority(score)
        reason = _reason_anta(weekly_sales, weekly_revenue, monthly_sales, stock, role, activity_fit)
        row_has_warning = False
        if stock < 20 and weekly_sales >= 50:
            warnings.append(f"第{index}行库存偏低但销量较高，请确认是否能参与主推")
            row_has_warning = True
        if weekly_revenue == Decimal("0") and weekly_sales > 0:
            warnings.append(f"第{index}行有销量但销售额为0，请复核源数据")
            row_has_warning = True
        if priority == "高":
            high_priority_count += 1
        total_score += score
        output_rows.append(
            {
                "项目": PROJECT_ANTA,
                "品牌": PROJECT_ANTA,
                "平台": platform,
                "款号": product_code,
                "商品名称": product_name,
                "大类": major_category,
                "类目": category,
                "近7天销量": str(weekly_sales),
                "近7天销售额": _format_decimal(weekly_revenue),
                "近30天销量": str(monthly_sales),
                "库存": str(stock),
                "场景主题": theme,
                "选品角色": role,
                "活动匹配度": str(activity_fit),
                "AI选品分": _format_decimal(score),
                "推荐优先级": priority,
                "推荐理由": reason,
                "人工复核": "需要" if row_has_warning else "建议复核",
            }
        )

    return _build_result(output_rows, total_score, high_priority_count, warnings)


def _resolve_project(row: dict[str, str]) -> str:
    if not isinstance(row, dict):
        raise TypeError("row must be dict")
    raw_project = str(row.get("项目") or "").strip()
    if raw_project:
        return raw_project
    if "款号" in row and "近7天销量" in row:
        return PROJECT_ANTA
    return PROJECT_GENERIC


def _parse_activity_fit(row: dict[str, str], index: int) -> int:
    activity_fit = parse_non_negative_int(row.get("活动匹配度"), f"第{index}行活动匹配度")
    if activity_fit > 100:
        raise ValidationError(f"第{index}行活动匹配度不能大于100")
    assert 0 <= activity_fit <= 100
    return activity_fit


def _score_generic(sales: int, stock: int, gross_margin: Decimal, activity_fit: int) -> Decimal:
    sales_score = min(Decimal(sales) / Decimal("300") * Decimal("35"), Decimal("35"))
    stock_score = min(Decimal(stock) / Decimal("200") * Decimal("20"), Decimal("20"))
    margin_score = gross_margin / Decimal("100") * Decimal("25")
    fit_score = Decimal(activity_fit) / Decimal("100") * Decimal("20")
    score = (sales_score + stock_score + margin_score + fit_score).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    assert score >= Decimal("0")
    return score


def _score_anta(
    weekly_sales: int,
    weekly_revenue: Decimal,
    monthly_sales: int,
    stock: int,
    role: str,
    activity_fit: int,
) -> Decimal:
    weekly_sales_score = min(Decimal(weekly_sales) / Decimal("100") * Decimal("35"), Decimal("35"))
    revenue_score = min(weekly_revenue / Decimal("50000") * Decimal("20"), Decimal("20"))
    monthly_sales_score = min(Decimal(monthly_sales) / Decimal("300") * Decimal("15"), Decimal("15"))
    stock_score = min(Decimal(stock) / Decimal("200") * Decimal("20"), Decimal("20"))
    role_score = ROLE_SCORES[role]
    fit_score = Decimal(activity_fit) / Decimal("100") * Decimal("10")
    score = (weekly_sales_score + revenue_score + monthly_sales_score + stock_score + role_score + fit_score).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    assert score >= Decimal("0")
    return score


def _priority(score: Decimal) -> str:
    if score >= Decimal("75"):
        return "高"
    if score >= Decimal("55"):
        return "中"
    return "低"


def _reason_generic(sales: int, stock: int, gross_margin: Decimal, activity_fit: int) -> str:
    reasons: list[str] = []
    if sales >= 200:
        reasons.append("近期销量强")
    if stock >= 100:
        reasons.append("库存可支撑")
    if gross_margin >= Decimal("30"):
        reasons.append("毛利空间较好")
    if activity_fit >= 80:
        reasons.append("活动匹配度高")
    if not reasons:
        return "建议作为备选，需业务确认卖点和库存"
    return "、".join(reasons)


def _reason_anta(weekly_sales: int, weekly_revenue: Decimal, monthly_sales: int, stock: int, role: str, activity_fit: int) -> str:
    reasons: list[str] = []
    if weekly_sales >= 50:
        reasons.append("近7天动销强")
    if weekly_revenue >= Decimal("10000"):
        reasons.append("周销售额贡献高")
    if monthly_sales >= 200:
        reasons.append("近30天稳定动销")
    if stock >= 100:
        reasons.append("库存可支撑")
    if role == "核心推荐":
        reasons.append("适合作为本周主推")
    if activity_fit >= 80:
        reasons.append("场景匹配度高")
    if not reasons:
        return "建议作为备选，需业务确认卖点、库存和平台资源"
    return "、".join(reasons)


def _build_result(
    output_rows: list[dict[str, str]],
    total_score: Decimal,
    high_priority_count: int,
    warnings: list[str],
) -> ProcessingResult:
    if not output_rows:
        raise ValidationError("选品结果不能为空")
    average_score = (total_score / Decimal(len(output_rows))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    summary = {
        "处理商品数": str(len(output_rows)),
        "高优先级商品数": str(high_priority_count),
        "平均选品分": _format_decimal(average_score),
    }
    result = ProcessingResult(module=MODULE_KEY, output_rows=output_rows, summary=summary, warnings=warnings)
    assert result.output_rows
    return result


def _format_decimal(value: Decimal) -> str:
    return str(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
