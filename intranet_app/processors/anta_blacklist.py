from __future__ import annotations

from ..domain import ProcessingResult, require_choice, require_text


MODULE_KEY = "anta_blacklist"
REQUIRED_FIELDS = ("品牌", "平台", "店铺", "账号标识", "动作", "原因", "提交人")
ACTION_MAP = {"加入黑名单": "BLOCK", "移出黑名单": "UNBLOCK"}


def process(rows: list[dict[str, str]]) -> ProcessingResult:
    if not isinstance(rows, list):
        raise TypeError("rows must be list")
    output_rows: list[dict[str, str]] = []
    warnings: list[str] = []
    seen: set[tuple[str, str, str]] = set()
    for index, row in enumerate(rows, start=2):
        if not isinstance(row, dict):
            raise TypeError("each row must be dict")
        account = require_text(row.get("账号标识"), f"第{index}行账号标识")
        action = require_choice(row.get("动作"), f"第{index}行动作", ACTION_MAP.keys())
        platform = require_text(row.get("平台"), f"第{index}行平台")
        shop = require_text(row.get("店铺"), f"第{index}行店铺")
        unique_key = (platform, shop, account)
        if unique_key in seen:
            warnings.append(f"第{index}行账号在同一平台店铺重复出现，请复核")
        seen.add(unique_key)
        output_rows.append(
            {
                "品牌": require_text(row.get("品牌"), f"第{index}行品牌"),
                "平台": platform,
                "店铺": shop,
                "账号标识_脱敏": _mask_account(account),
                "动作": action,
                "导入动作编码": ACTION_MAP[action],
                "原因": require_text(row.get("原因"), f"第{index}行原因"),
                "提交人": require_text(row.get("提交人"), f"第{index}行提交人"),
                "处理状态": "待导入",
            }
        )
    summary = {"处理行数": str(len(output_rows)), "加入数量": _count_action(output_rows, "加入黑名单"), "移出数量": _count_action(output_rows, "移出黑名单")}
    result = ProcessingResult(module=MODULE_KEY, output_rows=output_rows, summary=summary, warnings=warnings)
    assert result.output_rows
    return result


def _mask_account(account: str) -> str:
    if len(account) <= 4:
        return "*" * len(account)
    return f"{account[:2]}{'*' * (len(account) - 4)}{account[-2:]}"


def _count_action(rows: list[dict[str, str]], action: str) -> str:
    return str(sum(1 for row in rows if row.get("动作") == action))

