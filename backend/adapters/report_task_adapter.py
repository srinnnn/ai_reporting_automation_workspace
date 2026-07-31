from __future__ import annotations

from datetime import datetime
from typing import Protocol, runtime_checkable


@runtime_checkable
class CurrentUser(Protocol):
    username: str


ANTA_MEITUAN_DAILY_BRAND_ID = "anta_kids"
ANTA_MEITUAN_DAILY_BRAND_NAME = "\u5b89\u8e0f\u513f\u7ae5"
ANTA_MEITUAN_DAILY_BUSINESS_UNIT = "anta_retail_team"
ANTA_MEITUAN_DAILY_PLATFORM = "meituan"
ANTA_MEITUAN_DAILY_CHANNEL = "instant_retail"
FOUNDATION_ONLY_SOURCE_POLICY = "foundation_only"


def build_daily_report_task_payload(report_date: str, current_user: CurrentUser) -> dict[str, str]:
    if not isinstance(current_user, CurrentUser):
        raise TypeError("current_user must provide username")
    if not current_user.username.strip():
        raise ValueError("current_user username must not be empty")
    compact_date = _compact_report_date(report_date)
    payload = {
        "task_name": f"{ANTA_MEITUAN_DAILY_BRAND_NAME}\u7f8e\u56e2\u65e5\u62a5-{compact_date}",
        "business_unit": ANTA_MEITUAN_DAILY_BUSINESS_UNIT,
        "brand_id": ANTA_MEITUAN_DAILY_BRAND_ID,
        "brand_name": ANTA_MEITUAN_DAILY_BRAND_NAME,
        "brand": ANTA_MEITUAN_DAILY_BRAND_NAME,
        "platform": ANTA_MEITUAN_DAILY_PLATFORM,
        "channel": ANTA_MEITUAN_DAILY_CHANNEL,
        "report_type": "daily",
        "report_period": "daily",
        "date": compact_date,
        "report_date": compact_date,
        "date_window": compact_date,
        "source_policy": FOUNDATION_ONLY_SOURCE_POLICY,
        "frequency": "daily",
        "scheduled_time": "09:30",
        "output_folder": "runtime/results",
        "created_by": current_user.username.strip(),
    }
    assert payload["report_date"] == compact_date
    assert payload["source_policy"] == FOUNDATION_ONLY_SOURCE_POLICY
    return payload


def _compact_report_date(report_date: str) -> str:
    if not isinstance(report_date, str) or not report_date.strip():
        raise ValueError("report_date must not be empty")
    normalized = report_date.strip()
    if len(normalized) == 8 and normalized.isdigit():
        datetime.strptime(normalized, "%Y%m%d")
        return normalized
    if len(normalized) == 10 and normalized[4] == "-" and normalized[7] == "-":
        parsed = datetime.strptime(normalized, "%Y-%m-%d")
        return parsed.strftime("%Y%m%d")
    raise ValueError("report_date must use YYYYMMDD or YYYY-MM-DD")
