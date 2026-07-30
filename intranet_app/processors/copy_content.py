from __future__ import annotations

from dataclasses import dataclass

from ..domain import ProcessingResult, require_text


MODULE_KEY = "copy_content"
REQUIRED_FIELDS = (
    "品牌",
    "平台",
    "内容类型",
    "商品名称",
    "核心卖点",
    "目标人群",
    "活动利益点",
    "品牌调性",
    "禁用词",
    "内容主题",
    "开场文案",
    "使用场景",
    "品牌背书",
)


def process(rows: list[dict[str, str]]) -> ProcessingResult:
    if not isinstance(rows, list):
        raise TypeError("rows must be list")
    output_rows: list[dict[str, str]] = []
    warnings: list[str] = []
    pass_count = 0

    for index, row in enumerate(rows, start=2):
        if not isinstance(row, dict):
            raise TypeError("each row must be dict")
        parsed = _parse_row(row, index)
        title = _build_title(parsed)
        body = _build_body(parsed)
        combined = f"{title} {body}"
        hit_words = _hit_forbidden_words(combined, parsed.forbidden_words)
        status = "通过" if not hit_words else "需修改"
        if status == "通过":
            pass_count += 1
        else:
            warnings.append(f"第{index}行命中禁用词：{', '.join(hit_words)}")
        output_rows.append(
            {
                "品牌": parsed.brand,
                "平台": parsed.platform,
                "内容类型": parsed.content_type,
                "商品名称": parsed.product_name,
                "AI标题建议": title,
                "AI正文建议": body,
                "品牌调性": parsed.tone,
                "合规状态": status,
                "命中禁用词": ", ".join(hit_words) if hit_words else "无",
                "人工复核": "需要" if hit_words else "建议复核",
            }
        )

    summary = {
        "处理内容数": str(len(output_rows)),
        "初检通过数": str(pass_count),
        "需修改数": str(len(output_rows) - pass_count),
    }
    result = ProcessingResult(module=MODULE_KEY, output_rows=output_rows, summary=summary, warnings=warnings)
    assert result.output_rows
    return result


@dataclass(frozen=True)
class _ParsedCopyRequest:
    brand: str
    platform: str
    content_type: str
    product_name: str
    selling_points: tuple[str, ...]
    target_audience: str
    promotion: str
    tone: str
    forbidden_words: tuple[str, ...]
    content_theme: str
    opening_copy: str
    usage_scenarios: str
    brand_endorsement: str


def _parse_row(row: dict[str, str], index: int) -> _ParsedCopyRequest:
    forbidden_text = require_text(row.get("禁用词"), f"第{index}行禁用词")
    forbidden_words = tuple(word.strip() for word in forbidden_text.replace("，", ",").split(",") if word.strip())
    selling_points_text = require_text(row.get("核心卖点"), f"第{index}行核心卖点")
    selling_points = _split_selling_points(selling_points_text, index)
    result = _ParsedCopyRequest(
        brand=require_text(row.get("品牌"), f"第{index}行品牌"),
        platform=require_text(row.get("平台"), f"第{index}行平台"),
        content_type=require_text(row.get("内容类型"), f"第{index}行内容类型"),
        product_name=require_text(row.get("商品名称"), f"第{index}行商品名称"),
        selling_points=selling_points,
        target_audience=require_text(row.get("目标人群"), f"第{index}行目标人群"),
        promotion=require_text(row.get("活动利益点"), f"第{index}行活动利益点"),
        tone=require_text(row.get("品牌调性"), f"第{index}行品牌调性"),
        forbidden_words=forbidden_words,
        content_theme=require_text(row.get("内容主题"), f"第{index}行内容主题"),
        opening_copy=require_text(row.get("开场文案"), f"第{index}行开场文案"),
        usage_scenarios=require_text(row.get("使用场景"), f"第{index}行使用场景"),
        brand_endorsement=require_text(row.get("品牌背书"), f"第{index}行品牌背书"),
    )
    assert result.product_name
    return result


def _build_title(request: _ParsedCopyRequest) -> str:
    if not isinstance(request, _ParsedCopyRequest):
        raise TypeError("request must be _ParsedCopyRequest")
    title = f"{request.content_theme}｜{request.brand}{request.product_name}"
    assert title.strip()
    return title


def _build_body(request: _ParsedCopyRequest) -> str:
    if not isinstance(request, _ParsedCopyRequest):
        raise TypeError("request must be _ParsedCopyRequest")
    paragraphs = [
        request.opening_copy,
        _ensure_sentence(f"{request.brand}{request.product_name}，专为{request.usage_scenarios}设计"),
        *(_ensure_sentence(point) for point in request.selling_points),
        request.brand_endorsement,
        f"（{request.promotion}）",
    ]
    body = "\n".join(paragraph.strip() for paragraph in paragraphs if paragraph.strip())
    assert body.strip()
    return body


def _split_selling_points(value: str, index: int) -> tuple[str, ...]:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("value must be non-empty str")
    if not isinstance(index, int) or index < 2:
        raise ValueError("index must be an Excel data row number")
    points = tuple(point.strip() for point in value.replace("／", "/").split("/") if point.strip())
    if not points:
        raise ValueError(f"第{index}行核心卖点至少需要一项")
    assert all(points)
    return points


def _ensure_sentence(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("value must be non-empty str")
    text = value.strip()
    result = text if text.endswith(("。", "！", "？", "～", "~")) else f"{text}。"
    assert result.strip()
    return result


def _hit_forbidden_words(content: str, forbidden_words: tuple[str, ...]) -> list[str]:
    if not forbidden_words:
        return []
    return [word for word in forbidden_words if word and word in content]
