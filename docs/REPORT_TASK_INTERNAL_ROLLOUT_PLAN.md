# Report Task Internal Rollout Plan

## 1. Current Acceptance Conclusion

Scope: Anta Meituan daily report Task mode.

Current validation source:

- Batch consistency report: `runtime/consistency_reports/anta_meituan_daily_consistency_20260715_20260725.csv`
- Production acceptance document: `docs/REPORT_TASK_PRODUCTION_ACCEPTANCE.md`

Conclusion:

- Dates with complete foundation data passed Legacy vs Task consistency validation.
- PASS dates: 20260720, 20260721, 20260722, 20260723, 20260724, 20260725.
- For PASS dates, row count delta is 0, amount delta is 0.00, and no core field difference was found.
- Task result assets and download information were available for PASS dates.
- FAIL dates 20260715 to 20260719 failed in both Legacy and Task mode with the same validation error.
- The FAIL dates are classified as foundation data availability issues, not Task migration defects.

Rollout implication:

- Internal rollout can proceed only for dates with confirmed complete foundation data.
- Historical dates with missing completed-order data must be excluded or clearly marked as no-data scenarios until business confirmation or data backfill is complete.

## 2. Rollout Scope

### Admin Test Users

Purpose:

- Validate operational behavior before exposing Task mode to business users.
- Confirm Console visibility, task status readability, result asset creation, and download behavior.

Allowed activities:

- Generate Anta Meituan daily reports for validated dates.
- Check Task Center and Task Detail pages.
- Download generated CSV files.
- Record failures without changing report logic.

Recommended accounts:

- System admin account.
- Developer/admin operator account.

### Designated Business Users

Purpose:

- Validate business usability and output acceptance.
- Confirm whether Task-mode delivery can replace legacy manual waiting flow.

Allowed activities:

- Generate Anta Meituan daily reports for confirmed complete-data dates.
- Review CSV output.
- Compare output with familiar business delivery expectations.
- Provide feedback on result correctness, page clarity, waiting time, and download experience.

Recommended user scope:

- One Anta business owner.
- One daily report operator.
- One reviewer who receives the final report.

Excluded scope:

- Weekly report.
- Monthly report.
- AI content generation.
- Historical backfill dates with unresolved missing data.
- Cross-brand rollout.

## 3. Validation Flow

### Step 1: Enable Task Mode in Test Environment

Set:

```text
REPORT_TASK_MODE=task
```

Keep rollback ready:

```text
REPORT_TASK_MODE=legacy
```

Do not delete or disable the legacy flow.

### Step 2: Submit Daily Report

User action:

1. Open Anta Meituan daily report page.
2. Select a validated report date, such as 20260720 to 20260725.
3. Submit daily report generation.

Expected behavior:

- Page submits the same business request.
- Backend builds Task payload through the report task adapter.
- Task is submitted as `REPORT_GENERATE`.

### Step 3: Task Execution

Expected execution chain:

```text
ReportTaskAdapter
↓
TaskSubmitter
↓
TaskRunner
↓
ReportExecutor
↓
ReportService
↓
ResultAssetService
```

Validation points:

- Task status becomes `success` for complete-data dates.
- Failed status must contain clear error text.
- No processor logic is changed.
- No report formula is changed.

### Step 4: Console Review

User action:

1. Open Developer Console.
2. Enter Task Center.
3. Locate the submitted daily report task.
4. Open Task Detail.

Expected display:

- task_id
- task_type
- status
- created_by
- created_time
- result summary
- result asset status
- download availability
- failure message if failed

### Step 5: Result Download

User action:

1. Click download from Task Detail or Task result access page.
2. Open the downloaded CSV.
3. Compare with expected daily report output.

Expected behavior:

- CSV can be downloaded successfully.
- CSV header remains unchanged.
- CSV row count matches legacy validation for the same date.
- Business user can use the file without manual transformation.

### Step 6: Feedback Collection

Collect feedback for each validation attempt:

| Field | Description |
| --- | --- |
| user | Validator name or account |
| date | Report date |
| task_id | Generated task id |
| task_status | success or failed |
| output_accepted | yes or no |
| download_ok | yes or no |
| issue_type | data, task, report, asset, UX |
| comment | Business feedback |

## 4. Acceptance Metrics

### Success Rate

Definition:

```text
success tasks / submitted tasks
```

Acceptance target:

- Admin test users: 100% for confirmed complete-data dates.
- Designated business users: at least 95%, excluding confirmed data-missing dates.

Failure handling:

- Same Legacy and Task data-missing validation error: classify as data issue.
- Task-only failure: rollout blocker.
- Report mismatch: rollout blocker.

### Execution Time

Definition:

```text
time from task submission to task success or failed status
```

Acceptance target:

- Admin validation: record baseline manually.
- Business validation: execution should be acceptable for daily report operation and should not exceed the current manual tolerance.

Current limitation:

- Formal p50/p95 timing is not yet persisted in the task read model.
- During internal rollout, execution time can be recorded manually from submit time and Task Detail updated time.

### Download Success Rate

Definition:

```text
successful downloads / successful tasks with result_asset
```

Acceptance target:

- 100% for successful Task-mode daily reports.

Rollout blocker:

- Task status is success, but result asset is missing.
- Task status is success, but download fails.
- Download exposes unsafe path or server runtime path.

### User Feedback

Acceptance target:

- Business user confirms the generated CSV is usable.
- Business user confirms output fields match the current delivery expectation.
- Business user confirms the Task Center and download flow are understandable.

Feedback classification:

- data issue
- task issue
- report issue
- asset/download issue
- UX issue

## 5. Rollback Plan

Rollback trigger:

- Task-only failure occurs.
- Task result differs from Legacy result for complete-data dates.
- Result asset or download fails for successful tasks.
- Business user rejects output correctness.
- Console or task state causes operational confusion that blocks daily work.

Rollback action:

Set:

```text
REPORT_TASK_MODE=legacy
```

Then restart the application process if required by the runtime environment.

Rollback requirements:

- Do not delete Task code.
- Do not delete generated task records.
- Do not modify processor logic.
- Do not modify report calculation formulas.
- Keep legacy daily report generation available.

Post-rollback checks:

1. Generate one known good daily report in legacy mode.
2. Confirm legacy CSV downloads normally.
3. Record the failed Task task_id and error classification.
4. Fix only after reproducing the issue in a controlled test.

## 6. Restrictions

This internal rollout plan does not permit changes to:

- processor
- ReportService report calculation logic
- database schema
- Task execution logic
- Redis
- Celery
- PostgreSQL

## 7. Recommended Next Step

Proceed with Phase 1 admin validation using dates 20260720 to 20260725.

If Phase 1 passes, invite the designated Anta business user to validate the same date set before enabling Task mode for broader use.
