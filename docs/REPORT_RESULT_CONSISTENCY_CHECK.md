# Report Result Consistency Check

## Purpose

This check verifies that Anta Meituan daily report output is consistent between the legacy route behavior and the new Task-mode execution path.

The check is validation-only. It must not change:

- report processor logic
- report formulas
- output field definitions
- database schema
- default `REPORT_TASK_MODE=legacy`

## Compared Paths

### Legacy path under test

1. Build `MeituanReportSources` from the same foundation fixture rows.
2. Call `anta_meituan_reporting.build_meituan_daily_report(...)` directly, matching the existing legacy route calculation boundary.
3. Save output rows with existing `write_csv(...)`.

### Task path under test

1. Build the daily task payload with `build_daily_report_task_payload(...)`.
2. Submit `TaskType.REPORT_GENERATE` through `TaskSubmitter`.
3. Dispatch through `TaskRunner` to `ReportExecutor`.
4. Generate the report through `ReportService` from the same foundation fixture repository.
5. Persist the CSV through `ResultAssetService`.
6. Resolve the file through `TaskResultService`.

## Consistency Rules

The test compares:

1. Output row count
   - `legacy_rows`
   - `task_rows`

2. Core values
   - report date
   - top store
   - top product
   - sales amount
   - sales quantity

3. CSV structure
   - both files exist
   - filenames are generated
   - headers match exactly
   - field count matches

4. Task result
   - task status is `success`
   - `result_asset` exists
   - `TaskResultService.get_download_info(...)` resolves the generated CSV

## Risk Notes

- Task mode is still synchronous in this phase.
- Task mode stores the delivery CSV as a task result asset, not as a legacy job record.
- Business rollout should keep `REPORT_TASK_MODE=legacy` until consistency checks pass on real historical dates.
