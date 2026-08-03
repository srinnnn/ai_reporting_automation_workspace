# Report Task Rollout Execution

## 1. Current State

### Legacy Flow

Default mode remains:

```text
REPORT_TASK_MODE=legacy
```

Current legacy Anta Meituan daily report flow:

1. User submits `POST /anta-reporting/meituan-daily/run`.
2. Route syncs Meituan plugin download files.
3. Route imports available files into the unified foundation layer.
4. Route reads foundation-backed daily report sources.
5. Existing `anta_meituan_reporting` processor generates the report.
6. Legacy `write_csv` saves the delivery CSV.
7. Legacy job record is saved and downloaded through the existing job flow.

Legacy guarantees:

- Processor logic is unchanged.
- Report formulas are unchanged.
- CSV output fields are unchanged.
- Legacy job download remains available.

### Task Flow

Opt-in mode:

```text
REPORT_TASK_MODE=task
```

Task-mode Anta Meituan daily report flow:

1. User submits the same daily report page.
2. Route builds payload through `ReportTaskAdapter`.
3. `TaskSubmitter` creates a task and dispatches it through `TaskRunner`.
4. `ReportExecutor` calls `ReportService`.
5. `ReportService` reads the unified foundation layer and calls the unchanged processor.
6. `ResultAssetService` saves the CSV result asset.
7. `TaskResultService` exposes safe result metadata and download information.

Task-mode guarantees:

- No processor changes.
- No formula changes.
- No output field changes.
- No database schema changes.
- No Redis/Celery/PostgreSQL dependency in this phase.

### Consistency Validation Result

Current automated validation coverage:

- Single-date consistency check exists in `tests/test_daily_report_consistency.py`.
- Date-range batch consistency runner exists in `scripts/report_consistency_runner.py`.
- Batch validation document exists in `docs/REPORT_BATCH_CONSISTENCY_CHECK.md`.
- Full test suite passed after Step 10-C: `257 tests OK`.

Required before business rollout:

- Run real foundation data check for historical dates, for example `20260715` to `20260725`.
- Confirm every date has `PASS` in the batch consistency report.
- Review failed dates and confirm failures are caused by missing foundation data rather than task-mode calculation differences.

## 2. Rollout Phases

### Phase 1: Internal Developer Validation

Scope:

- Developers only.
- Local or controlled test environment only.
- Keep production/default mode as `legacy`.

Actions:

1. Run full unit tests.
2. Run batch consistency check for historical foundation dates.
3. Manually test one daily report in `REPORT_TASK_MODE=task`.
4. Verify task detail page and result download.

Exit criteria:

- Full tests pass.
- Batch consistency report has no unexpected `FAIL` rows.
- Task-generated CSV is downloadable through Task result flow.
- No processor, formula, field, or schema change is required.

### Phase 2: Designated Business User Validation

Scope:

- Limited users only.
- One brand/channel: Anta Kids + Meituan instant retail daily report.
- Continue keeping broad team default as `legacy` unless the environment is explicitly switched for validation.

Actions:

1. Select 1-2 business users who already know the daily report output.
2. Generate the same selected dates in legacy and task mode.
3. Compare CSV files and report copy output.
4. Ask users to validate whether download, status visibility, and error messages are acceptable.

Exit criteria:

- Result consistency confirmed by batch report and business review.
- Task success rate meets threshold.
- Download success rate meets threshold.
- No blocking user feedback.

### Phase 3: Formal Switch

Scope:

- Anta Meituan daily report only.
- Weekly report and other report routes remain legacy until separately migrated.

Actions:

1. Set:

```text
REPORT_TASK_MODE=task
```

2. Run smoke test for one current business date.
3. Confirm generated Task reaches `success`.
4. Confirm result asset can be downloaded.
5. Monitor failed tasks and download errors during the first operating window.

Exit criteria:

- Users can generate and download daily reports normally.
- No unexpected calculation or CSV field difference.
- No recurring task failure pattern.

## 3. Acceptance Metrics

### Result Consistency

Required:

- `legacy_rows == task_rows`
- CSV headers match exactly
- field count matches
- key metrics match:
  - date
  - store
  - product
  - sales amount
  - quantity

Recommended threshold:

- 100% pass for selected historical dates before formal switch.

### Task Success Rate

Required:

- Task status should be `success` for dates with complete foundation data.

Recommended threshold:

- Phase 1: 100% on test dates with complete data.
- Phase 2: 95%+ on business validation attempts, excluding confirmed missing-data cases.
- Phase 3: 98%+ after formal switch, excluding confirmed missing-data cases.

### File Download Success Rate

Required:

- `result_asset` exists for successful tasks.
- `TaskResultService.get_download_info()` resolves the file.
- User can download through the task result page/API.

Recommended threshold:

- 100% for successful tasks.

### User Feedback

Required:

- Business users can find the task result.
- Business users can understand failure messages.
- Business users can download the CSV without developer help.

Blocking feedback examples:

- Cannot locate output file.
- Output is different from legacy report.
- Failure message does not explain missing data or next action.

## 4. Rollback Plan

Immediate rollback switch:

```text
REPORT_TASK_MODE=legacy
```

Rollback scenarios:

- Task mode returns repeated `failed` status for complete foundation data.
- Result CSV differs from legacy output.
- Download failure appears for successful tasks.
- Business users cannot complete daily delivery within expected time.

Rollback steps:

1. Restore `REPORT_TASK_MODE=legacy`.
2. Restart the app if the environment variable is read at process startup.
3. Generate the daily report through the legacy path.
4. Preserve task failure records for diagnosis.
5. Do not delete Task code or legacy code.

Rollback validation:

- Legacy daily report can still generate CSV.
- Legacy job download still works.
- No database cleanup is required.

## 5. Monitoring Metrics

### Failed Task

Track:

- `task_id`
- `task_type`
- `brand_id`
- `platform`
- `channel`
- `report_date`
- error message
- created_by
- updated_at

Primary view:

- Developer Console Dashboard
- Task Center
- Task Detail diagnostics page

### Execution Time

Current phase:

- No formal timing table exists yet.
- Developers should manually record start/end around task submission during validation.

Future enhancement:

- Add task timing fields to formal task read model or `task_runs` schema.
- Track p50/p95 execution time after Celery/PostgreSQL migration.

### Download Failure

Track:

- successful task with missing `result_asset`
- missing local result file
- unsafe result path rejection
- permission denial

Required response:

- If download failure occurs while task status is `success`, treat as rollout blocker.

## 6. Explicit Non-Goals

This rollout does not include:

- weekly report task migration
- monthly report task migration
- Redis/Celery async worker
- PostgreSQL schema migration
- processor refactor
- formula changes
- output field changes

## 7. Recommended Next Step

Before switching any shared environment to `task`, run:

```powershell
$env:PYTHONPATH='.;src'
py -3.12 scripts/report_consistency_runner.py --start-date 20260715 --end-date 20260725 --output-dir runtime/consistency_reports
```

Review the generated CSV and only proceed when all expected dates are `PASS` or every `FAIL` has a confirmed missing-data explanation.
