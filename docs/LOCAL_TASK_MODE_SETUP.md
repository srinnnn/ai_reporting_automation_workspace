# Local Task Mode Setup

## Purpose

This document explains how to enable local Task mode for Anta Meituan daily report Phase 1 Admin validation.

The default runtime mode is safe rollback mode:

```text
REPORT_TASK_MODE=legacy
```

For local Phase 1 validation, use:

```text
REPORT_TASK_MODE=task
```

## Legacy Mode vs Task Mode

### Legacy Mode

```text
REPORT_TASK_MODE=legacy
```

Daily report execution path:

```text
Browser
↓
/anta-reporting/meituan-daily/run
↓
Legacy route
↓
Foundation-backed report generation
↓
Legacy job saved
↓
CSV download through job flow
```

Use this mode when:

- Business users need the stable existing workflow.
- Task validation fails.
- Rollback is required.

### Task Mode

```text
REPORT_TASK_MODE=task
```

Daily report execution path:

```text
Browser
↓
/anta-reporting/meituan-daily/run
↓
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
↓
TaskResult / Console / Task download
```

Use this mode only for local Admin Phase 1 validation until business acceptance is complete.

## How To Enable Task Mode Locally

Create or update the project root `.env` file:

```text
REPORT_TASK_MODE=task
```

Do not add secrets to `.env` for this validation.

Forbidden values in this local file:

- `SECRET_KEY`
- `ADMIN_PASSWORD`
- `DASHSCOPE_API_KEY`
- `TOKEN`
- passwords
- API keys

The current local `.env` should contain only:

```text
REPORT_TASK_MODE=task
```

## How To Restart The App

Stop the current local app process, then restart from the project root:

```powershell
py -3.12 -m intranet_app.app
```

If using an existing launcher, restart that launcher after saving `.env`.

## How To Verify Current Mode

Open:

```text
http://127.0.0.1:8785/console/environment
```

Expected value:

```text
REPORT_TASK_MODE = task
```

If the page still shows `legacy`:

1. Confirm `.env` exists in the project root.
2. Confirm it contains `REPORT_TASK_MODE=task`.
3. Restart the app process.
4. Reopen `/console/environment`.

## Phase 1 Validation Dates

Use these dates for Admin validation:

| Date | Expected Mode |
| --- | --- |
| 20260720 | task |
| 20260721 | task |
| 20260722 | task |
| 20260723 | task |
| 20260724 | task |
| 20260725 | task |

Record execution results in:

```text
docs/REPORT_TASK_PHASE1_EXECUTION_LOG.md
```

## How To Roll Back To Legacy

Edit `.env` and set:

```text
REPORT_TASK_MODE=legacy
```

Then restart the app.

Verify rollback through:

```text
http://127.0.0.1:8785/console/environment
```

Expected value after rollback:

```text
REPORT_TASK_MODE = legacy
```

## Safety Notes

- Do not commit `.env`.
- `.env` is ignored by Git.
- Do not store API keys, passwords, tokens, cookies, or business account credentials in `.env`.
- Task mode is still synchronous in this phase.
- PostgreSQL, Redis, and Celery are not enabled in this step.
