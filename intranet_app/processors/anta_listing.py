from __future__ import annotations

from ..domain import ProcessingResult, require_choice, require_text


MODULE_KEY = "anta_listing"
REQUIRED_FIELDS = ("品牌", "平台", "店铺", "SKU", "商品名称", "动作", "生效日期", "原因")
ACTION_MAP = {"上架": "ON", "下架": "OFF"}


def process(rows: list[dict[str, str]]) -> ProcessingResult:
    if not isinstance(rows, list):
        raise TypeError("rows must be list")
    output_rows: list[dict[str, str]] = []
    warnings: list[str] = []
    for index, row in enumerate(rows, start=2):
        if not isinstance(row, dict):
            raise TypeError("each row must be dict")
        action = require_choice(row.get("动作"), f"第{index}行动作", ACTION_MAP.keys())
        sku = require_text(row.get("SKU"), f"第{index}行SKU")
        output_rows.append(
            {
                "品牌": require_text(row.get("品牌"), f"第{index}行品牌"),
                "平台": require_text(row.get("平台"), f"第{index}行平台"),
                "店铺": require_text(row.get("店铺"), f"第{index}行店铺"),
                "SKU": sku,
                "商品名称": require_text(row.get("商品名称"), f"第{index}行商品名称"),
                "动作": action,
                "导入动作编码": ACTION_MAP[action],
                "生效日期": require_text(row.get("生效日期"), f"第{index}行生效日期"),
                "原因": require_text(row.get("原因"), f"第{index}行原因"),
                "处理状态": "待导入",
            }
        )
        if len(sku) < 4:
            warnings.append(f"第{index}行SKU长度偏短，请复核")
    summary = {"处理行数": str(len(output_rows)), "上架数量": _count_action(output_rows, "上架"), "下架数量": _count_action(output_rows, "下架")}
    result = ProcessingResult(module=MODULE_KEY, output_rows=output_rows, summary=summary, warnings=warnings)
    assert result.output_rows
    return result


def _count_action(rows: list[dict[str, str]], action: str) -> str:
    return str(sum(1 for row in rows if row.get("动作") == action))

