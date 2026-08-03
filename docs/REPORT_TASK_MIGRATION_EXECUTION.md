# Report Task Migration Execution

## Scope

This document records the first production migration step for Anta Meituan daily reporting. The goal is to support `REPORT_TASK_MODE=task` while keeping `REPORT_TASK_MODE=legacy` fully compatible.

## Legacy Route

Entry point:

`POST /anta-reporting/meituan-daily/run`

Current legacy call chain:

1. `IntranetApp._handle_anta_meituan_reporting_run(handler, user, "daily")`
2. `_read_urlencoded()` reads the selected report date.
3. `_sync_meituan_download_sources()` synchronizes plugin-downloaded Meituan files.
4. `_ingest_meituan_plugin_files_to_foundation(user.username)` imports synced files into the foundation layer.
5. `_load_anta_meituan_sources_from_foundation("daily", selected_report_date)` reads foundation-backed report sources.
6. `anta_meituan_reporting.build_meituan_daily_report(...)` calculates the report.
7. `write_csv(...)` writes the legacy delivery CSV.
8. `AppStorage.save_job(...)` records the legacy job.
9. `_result_page(...)` renders the legacy result page.

Legacy guarantees:

- Existing processor remains the calculation source.
- CSV output rows remain the same shape.
- Existing job download flow remains available.
- Existing sync and foundation import path remains available.

## Task Route

Feature flag:

`REPORT_TASK_MODE=task`

Task-mode call chain:

1. `IntranetApp._handle_anta_meituan_reporting_run(handler, user, "daily")`
2. `_read_urlencoded()` reads the selected report date.
3. `build_daily_report_task_payload(report_date, user)` creates a foundation-only payload.
4. `TaskSubmitter.submit(TaskType.REPORT_GENERATE, payload, user.username)` creates and runs the task.
5. `TaskRunner` dispatches to `ReportExecutor`.
6. `ReportExecutor` calls `ReportService`.
7. `ReportService` reads foundation rows through `FoundationRepository`.
8. `ReportService` calls the unchanged `anta_meituan_reporting` processor.
9. `ReportExecutor` saves CSV output through `ResultAssetService`.
10. `TaskSubmitter` saves the task result record.
11. `_task_result_page(...)` renders the task result.

Task-mode guarantees:

- No processor modification.
- No report formula modification.
- No database schema modification.
- Result asset persistence is handled through `ResultAssetService`.
- Download is exposed through `TaskResultService` and existing task download API.

## Differences

| Area | Legacy | Task mode |
| --- | --- | --- |
| User result | Legacy result page and job id | Task result page and task id |
| CSV persistence | `write_csv` directly under result dir | `ResultAssetService.save_csv` |
| Result tracking | `jobs` | `automation_tasks` + `automation_runs` |
| Download path | `/jobs/<id>/download` | `/api/tasks/<task_id>/download` |
| Execution style | Synchronous legacy route | Synchronous Task framework for now |
| Source policy | sync + import + foundation read | foundation-only payload, fail closed if missing data |

## Risks

1. Task mode does not create a legacy job record, so users must use Task pages/API for downloads.
2. Task mode relies on foundation data being ready; it must fail closed if required foundation rows are missing.
3. Task mode is still synchronous until Redis/Celery is introduced.
4. Task results use `automation_runs.message` for result payload persistence until the formal task read model schema exists.
5. Business users should remain on `REPORT_TASK_MODE=legacy` until acceptance testing confirms daily report parity.

## Validation Plan

1. Legacy mode regression: route uses the legacy sync/import/foundation/processor/write_csv flow.
2. Task mode submission: route uses adapter + TaskSubmitter and skips legacy sync.
3. ReportExecutor success: calls ReportService and saves CSV through ResultAssetService.
4. TaskResult download: TaskResultService can resolve the saved asset.
5. Failure path: executor/service failure returns `failed` and TaskSubmitter persists the failed run status.
