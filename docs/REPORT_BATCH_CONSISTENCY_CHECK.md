# Report Batch Consistency Check

## Purpose

`report_consistency_runner.py` validates Anta Meituan daily report parity across a real date range. It compares the legacy calculation path with the Task architecture path without changing report business logic.

## Command

From the project root:

```powershell
$env:PYTHONPATH='.;src'
py -3.12 scripts/report_consistency_runner.py --start-date 20260715 --end-date 20260725 --output-dir runtime/consistency_reports
```

Optional SQLite override:

```powershell
py -3.12 scripts/report_consistency_runner.py --start-date 20260715 --end-date 20260725 --database-path intranet_app/runtime/app.sqlite3
```

## Compared Paths

Legacy path:

1. Read foundation rows.
2. Build `MeituanReportSources`.
3. Call `anta_meituan_reporting.build_meituan_daily_report`.
4. Save CSV with `write_csv`.

Task path:

1. Build payload with `build_daily_report_task_payload`.
2. Submit `TaskType.REPORT_GENERATE` through `TaskSubmitter`.
3. Run `TaskRunner` and `ReportExecutor`.
4. Build report through `ReportService`.
5. Save CSV through `ResultAssetService`.
6. Resolve download info through `TaskResultService`.

## Daily Checks

For each date, the runner checks:

- row count: `legacy_rows` and `task_rows`
- core values: date, store, product, sales amount, quantity
- CSV structure: files exist, headers match, field count matches
- Task result: `status=success`, `result_asset` exists, `download_info` resolves

## Output Report

The runner writes:

`anta_meituan_daily_consistency_<start>_<end>.csv`

Columns:

| Column | Meaning |
| --- | --- |
| 日期 | Business date checked. |
| legacy_status | Legacy path execution status. |
| task_status | Task path execution status. |
| legacy_rows | Legacy CSV row count. |
| task_rows | Task CSV row count. |
| row_delta | `task_rows - legacy_rows`. |
| amount_delta | Task sales amount minus legacy sales amount. |
| field_diff | Header difference when CSV structures differ. |
| result | `PASS` or `FAIL`. |
| message | Failure reason or comparison mismatch. |

## Failure Handling

A single-day failure does not stop the range check. The runner records that date as `FAIL` and continues with the next date.

## Constraints

This tool must not modify:

- processor logic
- ReportService calculation logic
- report output field definitions
- database schema
- default `REPORT_TASK_MODE=legacy`

It does not introduce PostgreSQL, Redis, or Celery.
