from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Callable

from .domain import ProcessingResult, ValidationError


MODULE_KEY = "p2_content_center"
ANTA_DEFAULT_BRAND_PROFILE = (
    "安踏儿童，专业儿童运动品牌。表达应清晰、亲切、可信，面向家长时强调专业、舒适、场景适配；"
    "面向儿童时强调运动活力。不得编造材质、科技、价格、优惠、认证和库存信息。"
)
DEFAULT_FORBIDDEN_WORDS = ("最", "第一", "绝对", "永久", "100%", "治愈", "医疗", "神奇")


@dataclass(frozen=True)
class P2ContentRequest:
    brand_id: str
    brand_name: str
    platform: str
    channel: str
    start_date: str
    end_date: str
    task_type: str
    output_count: int
    brand_profile: str
    forbidden_words: tuple[str, ...]

    def __post_init__(self) -> None:
        for field_name, value in (
            ("brand_id", self.brand_id),
            ("brand_name", self.brand_name),
            ("platform", self.platform),
            ("channel", self.channel),
            ("start_date", self.start_date),
            ("end_date", self.end_date),
            ("task_type", self.task_type),
            ("brand_profile", self.brand_profile),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must not be empty")
        _parse_compact_date(self.start_date, "start_date")
        _parse_compact_date(self.end_date, "end_date")
        if self.start_date > self.end_date:
            raise ValidationError("开始日期不能晚于结束日期")
        if self.task_type not in {"social_copy", "poster_copy", "xiaohongshu_copy", "selection_brief"}:
            raise ValidationError("内容任务只能选择：social_copy、poster_copy、xiaohongshu_copy、selection_brief")
        if not isinstance(self.output_count, int) or self.output_count <= 0 or self.output_count > 20:
            raise ValidationError("输出数量必须在1到20之间")
        if not isinstance(self.forbidden_words, tuple):
            raise TypeError("forbidden_words must be tuple")


@dataclass(frozen=True)
class ProductCandidate:
    sku_code: str
    product_name: str
    category: str
    sales_quantity: Decimal
    paid_sales_amount: Decimal
    order_count: int
    review_count: int
    review_examples: tuple[str, ...]

    def __post_init__(self) -> None:
        for field_name, value in (
            ("sku_code", self.sku_code),
            ("product_name", self.product_name),
            ("category", self.category),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must not be empty")
        if self.sales_quantity < Decimal("0") or self.paid_sales_amount < Decimal("0"):
            raise ValueError("candidate metrics must not be negative")
        if self.order_count < 0 or self.review_count < 0:
            raise ValueError("candidate counts must not be negative")
        if not isinstance(self.review_examples, tuple):
            raise TypeError("review_examples must be tuple")


def build_p2_content_pack(
    request: P2ContentRequest,
    product_rows: list[dict[str, str]],
    review_rows: list[dict[str, str]],
    ai_generate_text: Callable[[str, str, int], str],
) -> ProcessingResult:
    if not isinstance(request, P2ContentRequest):
        raise TypeError("request must be P2ContentRequest")
    if not isinstance(product_rows, list):
        raise TypeError("product_rows must be list")
    if not isinstance(review_rows, list):
        raise TypeError("review_rows must be list")
    if not callable(ai_generate_text):
        raise TypeError("ai_generate_text must be callable")
    candidates = select_product_candidates(product_rows, review_rows, request)
    system_prompt = _system_prompt()
    user_prompt = _user_prompt(request, candidates)
    raw_ai_text = ai_generate_text(system_prompt, user_prompt, 2600)
    ai_items = _parse_ai_json(raw_ai_text)
    output_rows = _build_output_rows(request, candidates, ai_items)
    warnings = _quality_warnings(output_rows, request.forbidden_words)
    summary = {
        "模块": "P2内容生产中心",
        "品牌": request.brand_name,
        "平台": request.platform,
        "渠道": request.channel,
        "开始日期": request.start_date,
        "结束日期": request.end_date,
        "候选商品数": str(len(candidates)),
        "输出内容数": str(len(output_rows)),
        "AI生成状态": "已调用API生成",
    }
    result = ProcessingResult(module=MODULE_KEY, output_rows=output_rows, summary=summary, warnings=warnings)
    assert result.output_rows
    logging.info("P2 content pack built: brand=%s rows=%s", request.brand_id, len(output_rows))
    return result


def select_product_candidates(product_rows: list[dict[str, str]], review_rows: list[dict[str, str]], request: P2ContentRequest) -> list[ProductCandidate]:
    if not isinstance(request, P2ContentRequest):
        raise TypeError("request must be P2ContentRequest")
    if not product_rows:
        raise ValidationError("基础数据层缺少商品订单数据，P2内容生产不能直接读取原始下载文件。")
    review_map = _review_examples_by_product(review_rows, request)
    aggregates: dict[str, dict[str, object]] = {}
    for row in product_rows:
        if not isinstance(row, dict):
            raise TypeError("each product row must be dict")
        row_date = _compact_date_from_row(row.get("下单时间", "") or row.get("日期", ""))
        if row_date < request.start_date or row_date > request.end_date:
            continue
        status = str(row.get("订单状态", "")).strip()
        if status and "取消" in status:
            continue
        sku_code = str(row.get("商品SKU码", "") or row.get("UPC码", "")).strip()
        product_name = str(row.get("商品名称", "")).strip()
        if not sku_code or not product_name:
            continue
        item = aggregates.setdefault(
            sku_code,
            {
                "sku_code": sku_code,
                "product_name": product_name,
                "category": str(row.get("商品分类", "")).strip() or "未分类",
                "sales_quantity": Decimal("0"),
                "paid_sales_amount": Decimal("0"),
                "order_ids": set(),
            },
        )
        item["sales_quantity"] = item["sales_quantity"] + _decimal(row.get("商品销售数量", "0"), "商品销售数量")
        item["paid_sales_amount"] = item["paid_sales_amount"] + _decimal(row.get("商品实付销售额", "0"), "商品实付销售额")
        order_id = str(row.get("订单编号", "")).strip()
        if order_id:
            item["order_ids"].add(order_id)
    candidates = [
        ProductCandidate(
            sku_code=str(item["sku_code"]),
            product_name=str(item["product_name"]),
            category=str(item["category"]),
            sales_quantity=item["sales_quantity"],
            paid_sales_amount=item["paid_sales_amount"],
            order_count=len(item["order_ids"]),
            review_count=len(review_map.get(str(item["sku_code"]), ())),
            review_examples=review_map.get(str(item["sku_code"]), ())[:3],
        )
        for item in aggregates.values()
        if isinstance(item["sales_quantity"], Decimal) and isinstance(item["paid_sales_amount"], Decimal)
    ]
    candidates.sort(key=lambda item: (item.paid_sales_amount, item.sales_quantity, Decimal(item.order_count)), reverse=True)
    result = candidates[: request.output_count]
    if not result:
        raise ValidationError("当前日期范围内没有可用于P2内容生产的完成商品数据。")
    assert result
    return result


def _review_examples_by_product(review_rows: list[dict[str, str]], request: P2ContentRequest) -> dict[str, tuple[str, ...]]:
    result: dict[str, list[str]] = {}
    for row in review_rows:
        if not isinstance(row, dict):
            raise TypeError("each review row must be dict")
        raw_date = row.get("评价提交日期", "") or row.get("评价提交时间", "")
        if raw_date:
            row_date = _compact_date_from_row(raw_date)
            if row_date < request.start_date or row_date > request.end_date:
                continue
        product_text = str(row.get("订单商品", "")).strip()
        review_text = str(row.get("用户评价", "")).strip()
        if not product_text or not review_text:
            continue
        sku_tokens = re.findall(r"[A-Za-z]?\d{6,}[A-Za-z]?", product_text)
        for sku_code in sku_tokens:
            result.setdefault(sku_code, []).append(review_text[:120])
    compact = {sku_code: tuple(examples[:5]) for sku_code, examples in result.items()}
    assert isinstance(compact, dict)
    return compact


def _system_prompt() -> str:
    return (
        "你是电商内容生产Agent。你只能基于用户提供的商品事实、销售表现、评价摘录和品牌资料生成内容，"
        "不得编造材质、科技、价格、优惠、认证、库存、疗效或未给出的商品事实。"
        "必须只返回JSON，不要返回Markdown。"
    )


def _user_prompt(request: P2ContentRequest, candidates: list[ProductCandidate]) -> str:
    product_payload = [
        {
            "sku_code": item.sku_code,
            "product_name": item.product_name,
            "category": item.category,
            "sales_quantity": _format_decimal(item.sales_quantity),
            "paid_sales_amount": _format_decimal(item.paid_sales_amount),
            "order_count": item.order_count,
            "review_examples": list(item.review_examples),
        }
        for item in candidates
    ]
    payload = {
        "brand": request.brand_name,
        "platform": request.platform,
        "channel": request.channel,
        "date_window": {"start": request.start_date, "end": request.end_date},
        "task_type": request.task_type,
        "brand_profile": request.brand_profile,
        "forbidden_words": list(request.forbidden_words),
        "products": product_payload,
        "required_schema": {
            "items": [
                {
                    "sku_code": "必须来自输入products",
                    "target_audience": "目标人群",
                    "usage_scene": "使用场景",
                    "selling_points": ["每条必须能从商品名称/类目/评价/品牌资料推导"],
                    "copy_title": "标题",
                    "copy_body": "正文，适合业务群或社群发布",
                    "visual_brief": "图片或页面Brief",
                    "risk_flags": ["无法确认或需要人工补充的事项"],
                }
            ]
        },
    }
    result = json.dumps(payload, ensure_ascii=False)
    assert "products" in result
    return result


def _parse_ai_json(raw_ai_text: str) -> dict[str, dict[str, object]]:
    if not isinstance(raw_ai_text, str) or not raw_ai_text.strip():
        raise ValidationError("AI接口返回内容为空。")
    text = raw_ai_text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text, flags=re.IGNORECASE).strip()
        text = re.sub(r"```$", "", text).strip()
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValidationError("AI接口未返回合法JSON，请重试或降低输出数量。") from exc
    if not isinstance(payload, dict):
        raise ValidationError("AI接口返回JSON必须是对象。")
    items = payload.get("items")
    if not isinstance(items, list) or not items:
        raise ValidationError("AI接口返回JSON缺少items。")
    result: dict[str, dict[str, object]] = {}
    for item in items:
        if not isinstance(item, dict):
            raise ValidationError("AI接口items内每一项必须是对象。")
        sku_code = str(item.get("sku_code", "")).strip()
        if not sku_code:
            raise ValidationError("AI接口items缺少sku_code。")
        result[sku_code] = item
    assert result
    return result


def _build_output_rows(request: P2ContentRequest, candidates: list[ProductCandidate], ai_items: dict[str, dict[str, object]]) -> list[dict[str, str]]:
    output_rows: list[dict[str, str]] = []
    for index, candidate in enumerate(candidates, start=1):
        item = ai_items.get(candidate.sku_code)
        if item is None:
            raise ValidationError(f"AI接口结果缺少商品 {candidate.sku_code}。")
        output_rows.append(
            {
                "排序": str(index),
                "品牌": request.brand_name,
                "平台": request.platform,
                "渠道": request.channel,
                "任务类型": request.task_type,
                "日期范围": f"{request.start_date}-{request.end_date}",
                "款号/SKU": candidate.sku_code,
                "商品名称": candidate.product_name,
                "类目": candidate.category,
                "销售额": _format_decimal(candidate.paid_sales_amount),
                "销量": _format_decimal(candidate.sales_quantity),
                "订单数": str(candidate.order_count),
                "目标人群": _text(item.get("target_audience", "")),
                "使用场景": _text(item.get("usage_scene", "")),
                "卖点提炼": " / ".join(_list_text(item.get("selling_points", []))),
                "AI标题": _text(item.get("copy_title", "")),
                "AI正文": _text(item.get("copy_body", "")),
                "视觉Brief": _text(item.get("visual_brief", "")),
                "质检风险": " / ".join(_list_text(item.get("risk_flags", []))) or "未发现",
                "人工复核": "需要",
            }
        )
    assert output_rows
    return output_rows


def _quality_warnings(output_rows: list[dict[str, str]], forbidden_words: tuple[str, ...]) -> list[str]:
    warnings: list[str] = []
    for row in output_rows:
        content = f"{row.get('AI标题', '')}\n{row.get('AI正文', '')}\n{row.get('视觉Brief', '')}"
        hits = [word for word in forbidden_words if word and word in content]
        if hits:
            warnings.append(f"{row.get('款号/SKU', '')} 命中禁用词：{', '.join(hits)}")
        if row.get("质检风险", "") != "未发现":
            warnings.append(f"{row.get('款号/SKU', '')} 需要复核：{row.get('质检风险', '')}")
    if not warnings:
        warnings.append("AI输出未命中系统禁用词，但仍需业务复核商品事实、价格和活动信息。")
    assert warnings
    return warnings


def _text(value: object) -> str:
    if value is None:
        return ""
    result = str(value).strip()
    assert isinstance(result, str)
    return result


def _list_text(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        result = [str(item).strip() for item in value if str(item).strip()]
    else:
        result = [str(value).strip()] if str(value).strip() else []
    assert isinstance(result, list)
    return result


def _decimal(value: object, field_name: str) -> Decimal:
    text = str(value or "0").replace(",", "").replace("¥", "").strip()
    if not text:
        return Decimal("0")
    try:
        result = Decimal(text)
    except InvalidOperation as exc:
        raise ValidationError(f"{field_name}必须是数字") from exc
    if result < Decimal("0"):
        raise ValidationError(f"{field_name}不能小于0")
    assert result >= Decimal("0")
    return result


def _compact_date_from_row(value: object) -> str:
    text = str(value or "").strip()
    match = re.search(r"(20\d{2})[-/]?(\d{2})[-/]?(\d{2})", text)
    if match is None:
        raise ValidationError(f"日期格式无法识别：{text}")
    result = "".join(match.groups())
    _parse_compact_date(result, "日期")
    return result


def _parse_compact_date(value: str, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be str")
    text = value.strip().replace("-", "")
    if not re.fullmatch(r"20\d{6}", text):
        raise ValidationError(f"{field_name}必须是YYYYMMDD或YYYY-MM-DD")
    return text


def _format_decimal(value: Decimal) -> str:
    if not isinstance(value, Decimal):
        raise TypeError("value must be Decimal")
    result = str(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
    assert result
    return result
