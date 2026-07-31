# PostgreSQL Schema Design

This directory contains PostgreSQL design artifacts for the production database migration.

Current stage: Step 7-B - PostgreSQL Schema SQL Design.

## Files

- `schema.sql`: proposed PostgreSQL schema for production task, report, asset, and user metadata.

## Important Boundary

This is a design artifact only.

Do not run this SQL against production until the following work is complete:

1. Migration scripts are reviewed.
2. A SQLite export and PostgreSQL staging import have been tested.
3. Row-count and metric validation reports pass.
4. Backup and rollback scripts exist.
5. Repository adapters are implemented and tested.
6. A controlled cutover window is approved.

## Tables

### users

Stores login users compatible with the current `UserRecord` model.

The first PostgreSQL migration keeps `role` as a text field for compatibility. Formal RBAC tables should be added later.

### assets

Stores metadata for generated or uploaded files.

The database stores metadata only. File bytes remain in the configured result/upload storage root or future object storage.

### tasks

Stores the formal task read/write model.

It supports:

- task type
- status
- submitter
- owner
- brand/business/platform/channel scope
- payload JSON
- permission scope snapshot
- idempotency key

Valid task statuses:

```text
pending
running
success
failed
cancelled
```

### task_runs

Stores execution attempts for a task.

It supports:

- retries through `(task_id, attempt)`
- worker tracking
- queue name
- progress JSON
- structured error fields
- started and finished timestamps

### task_results

Stores downloadable task result metadata.

`TaskResultService` must continue to validate file paths before download and must not expose `storage_path` to the frontend.

### reports

Stores formal report delivery records for P1 daily, weekly, monthly, and future report outputs.

Reports can link to both `tasks` and `assets`.

## Design Notes

- `JSONB` fields are constrained to object or array shapes where applicable.
- Task status fields use `CHECK` constraints.
- String identifiers use `TEXT` and non-empty checks.
- File paths are stored as text metadata and must still be validated by service code.
- The schema includes indexes for task status pages, RBAC filtering, report lookup, asset lookup, and JSONB search.

## Migration Strategy

The intended migration path is:

```text
SQLite
  -> export
  -> transform
  -> PostgreSQL staging tables
  -> validation
  -> production tables
```

Repository migration should keep service interfaces stable:

```text
Service
  -> Repository Interface
  -> SQLite Adapter or PostgreSQL Adapter
```

SQLite development mode must remain available until the production cutover is validated.

## Safety Rules

- Do not store API keys in PostgreSQL.
- Do not store raw business Excel/CSV files in PostgreSQL.
- Do not expose `storage_path` through API responses.
- Do not use PostgreSQL as the storage backend for large binary files.
- Do not remove SQLite support before production migration is complete and rollback has been tested.
