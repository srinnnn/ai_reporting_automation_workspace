from __future__ import annotations

import csv
import logging
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

from intranet_app.app import _BytesReader
from intranet_app.config import DEFAULT_CONFIG
from intranet_app.domain import ValidationError
from intranet_app.io_utils import read_table, write_csv
from intranet_app.processors.anta_meituan_reporting import (
    MeituanReportSources,
    build_meituan_daily_report,
)


@dataclass(frozen=True)
class BatchDailyResult:
    report_date: str
    status: str
    output_path: str
    message: str

    def __post_init__(self) -> None:
        for field_name, field_value in (
            ("report_date", self.report_date),
            ("status", self.status),
            ("output_path", self.output_path),
            ("message", self.message),
        ):
            if not isinstance(field_value, str):
                raise TypeError(f"{field_name} must be str")
        if not self.report_date.strip():
            raise ValueError("report_date must not be empty")


def generate_batch(start_date: str, end_date: str, downloads_root: Path, output_root: Path) -> list[BatchDailyResult]:
    _validate_compact_date(start_date, "start_date")
    _validate_compact_date(end_date, "end_date")
    if start_date > end_date:
        raise ValidationError("start_date must not be later than end_date")
    if not isinstance(downloads_root, Path):
        raise TypeError("downloads_root must be Path")
    if not isinstance(output_root, Path):
        raise TypeError("output_root must be Path")
    product_rows = _load_broadest_rows(downloads_root, ("商品数据",), "下单时间", allow_empty=False)
    finance_daily_by_date = _load_exact_daily_rows(downloads_root, ("门店财务明细",), "开始时间")
    traffic_daily_by_date = _load_exact_daily_rows(downloads_root, ("门店流量明细",), "开始时间")
    review_rows = _load_broadest_rows(downloads_root, ("评价分析明细",), "评价提交日期", allow_empty=True)
    output_root.mkdir(parents=True, exist_ok=True)

    results: list[BatchDailyResult] = []
    for report_date in _date_range(start_date, end_date):
        product_for_day = [row for row in product_rows if _row_date(row, "下单时间") == report_date]
        if not product_for_day:
            results.append(BatchDailyResult(report_date, "missing", "", "缺少商品/订单明细，不能生成日报。"))
            continue
        sources = MeituanReportSources(
            product_rows=product_rows,
            finance_rows=finance_daily_by_date.get(report_date, []),
            traffic_rows=traffic_daily_by_date.get(report_date, []),
            review_rows=review_rows,
        )
        try:
            report = build_meituan_daily_report(sources, report_date)
            output_path = output_root / f"anta_meituan_daily_report_{report_date}.csv"
            write_csv(output_path, report.output_rows)
            message = "；".join(report.warnings) if report.warnings else "生成成功"
            results.append(BatchDailyResult(report_date, "generated", str(output_path), message))
        except (ValidationError, ValueError, TypeError) as exc:
            results.append(BatchDailyResult(report_date, "failed", "", str(exc)))
    _write_batch_index(output_root / "anta_meituan_daily_batch_index.csv", results)
    assert isinstance(results, list)
    return results


def _load_latest_rows(root: Path, tokens: tuple[str, ...], allow_empty: bool) -> list[dict[str, str]]:
    candidates = _matching_files(root, tokens)
    if not candidates:
        if allow_empty:
            return []
        raise FileNotFoundError(f"未找到源文件：{tokens}")
    selected = max(candidates, key=lambda path: (path.stat().st_mtime, path.name))
    logging.info("selected source file: %s", selected)
    return read_table(selected.name, _BytesReader(selected.read_bytes()))


def _load_broadest_rows(root: Path, tokens: tuple[str, ...], date_field: str, allow_empty: bool) -> list[dict[str, str]]:
    candidates = _matching_files(root, tokens)
    if not candidates:
        if allow_empty:
            return []
        raise FileNotFoundError(f"未找到源文件：{tokens}")
    scored: list[tuple[int, float, Path, list[dict[str, str]]]] = []
    for path in candidates:
        rows = read_table(path.name, _BytesReader(path.read_bytes()))
        dates = {
            _row_date(row, date_field)
            for row in rows
            if _row_date(row, date_field)
        }
        scored.append((len(dates), path.stat().st_mtime, path, rows))
    selected = max(scored, key=lambda item: (item[0], item[1], item[2].name))
    logging.info("selected broadest source file: %s", selected[2])
    return selected[3]


def _load_exact_daily_rows(root: Path, tokens: tuple[str, ...], date_field: str) -> dict[str, list[dict[str, str]]]:
    result: dict[str, list[dict[str, str]]] = {}
    for path in _matching_files(root, tokens):
        rows = read_table(path.name, _BytesReader(path.read_bytes()))
        dates = sorted({_row_date(row, date_field) for row in rows if _row_date(row, date_field)})
        end_dates = sorted({_row_date(row, "结束时间") for row in rows if _row_date(row, "结束时间")})
        if len(dates) == 1 and (not end_dates or end_dates == dates):
            result[dates[0]] = rows
    assert isinstance(result, dict)
    return result


def _matching_files(root: Path, tokens: tuple[str, ...]) -> list[Path]:
    if not root.exists():
        raise FileNotFoundError(f"目录不存在：{root}")
    return [
        path
        for path in root.rglob("*.csv")
        if path.is_file() and all(token in path.name for token in tokens)
    ]


def _write_batch_index(path: Path, results: list[BatchDailyResult]) -> None:
    if not isinstance(path, Path):
        raise TypeError("path must be Path")
    if not isinstance(results, list):
        raise TypeError("results must be list")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["report_date", "status", "output_path", "message"])
        writer.writeheader()
        for item in results:
            writer.writerow(
                {
                    "report_date": item.report_date,
                    "status": item.status,
                    "output_path": item.output_path,
                    "message": item.message,
                }
            )


def _date_range(start_date: str, end_date: str) -> list[str]:
    start = _validate_compact_date(start_date, "start_date")
    end = _validate_compact_date(end_date, "end_date")
    values: list[str] = []
    current = start
    while current <= end:
        values.append(current.strftime("%Y%m%d"))
        current += timedelta(days=1)
    assert values
    return values


def _validate_compact_date(value: str, field_name: str) -> date:
    if not isinstance(value, str) or len(value) != 8 or not value.isdigit():
        raise ValidationError(f"{field_name} must be YYYYMMDD")
    try:
        return date(int(value[:4]), int(value[4:6]), int(value[6:8]))
    except ValueError as exc:
        raise ValidationError(f"{field_name} must be a valid date") from exc


def _row_date(row: dict[str, str], field_name: str) -> str:
    if not isinstance(row, dict):
        raise TypeError("row must be dict")
    text = row.get(field_name, "").strip()
    digits = "".join(ch for ch in text if ch.isdigit())
    return digits[:8] if len(digits) >= 8 else ""


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    output_root = DEFAULT_CONFIG.result_dir / "anta_meituan_daily_20260715_20260725"
    results = generate_batch("20260715", "20260725", Path.home() / "Downloads", output_root)
    for item in results:
        print(f"{item.report_date},{item.status},{item.output_path},{item.message}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
