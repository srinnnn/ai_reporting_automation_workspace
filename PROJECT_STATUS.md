# Project Status

## Completed

- Local intranet workbench with login, dashboard, P1-P4 priority pages, project stage page, and feedback fields.
- Data intake and archive indexing pages.
- Unified data foundation flow for Meituan Anta Kids data: recognition, mapping, validation, brand ownership check, and fact-table import.
- Foundation fact tables for product orders, store finance, store traffic, and service reviews.
- Anta Meituan daily and weekly report generation from the unified foundation data layer.
- Meituan browser download assistant and local sync path.
- Automation execution page for daily data sync, import, and validation.
- P2 content production center under the P2 secondary page.
- P2 pipeline for product selection, audience/scene, selling-point extraction, AI copy, visual brief, and quality flags.
- Bailian API configuration and connection test page.
- Anta instant retail entry for listing, material, and blacklist flows.
- Unit tests for processors, data foundation, reporting, automation, P2 content, AI gateway, and layout.
- Stage 3 Step 1 production foundation: added standalone backend core configuration, logging, and health-check modules without changing existing business flows.
- Stage 3 Step 2 repository boundary: added abstract repository interfaces and SQLite adapters backed by the existing `AppStorage`, without changing schema or business processors.
- Stage 3 Step 3 data foundation service: added a service-layer orchestration wrapper for existing file recognition, mapping, validation, check persistence, and foundation import behavior.
- Stage 3 Step 4 report service: added a service-layer wrapper for Meituan daily and weekly report generation from the foundation repository and report-result persistence through the report repository.
- Stage 3 Step 5 AI service layer: added AIService for Bailian-backed text generation, configuration status, timeout control, and retry boundary, plus AIContentService for P2 content orchestration through the existing content pipeline.
- Stage 3 Step 6-A task service foundation: added a unified TaskService boundary, task status model, and repository-compatible task result recording for future async worker migration without adding Redis/Celery or changing schema.
- Stage 3 Step 6-B worker contract design: added JSON-compatible TaskRequest and TaskResult models plus a BaseTaskExecutor interface for future Redis/Celery workers without changing runtime behavior.
- Stage 3 Step 6-C local executor adapter: migrated BaseTaskExecutor into the executors package and added local DataImportExecutor, ReportExecutor, and AIContentExecutor adapters that route through Service boundaries.
- Stage 3 Step 6-D task runner: added a unified TaskRunner that dispatches TaskRequest objects to registered executors and returns TaskResult objects without adding Redis/Celery or route wiring.
- Stage 3 Step 6-E task submission adapter: added TaskSubmitter to create task records through TaskService, build TaskRequest objects, dispatch through TaskRunner, and persist TaskResult status through TaskService.
- Stage 3 Step 6-F task read model: added TaskQueryService for read-only task detail, filtered task lists, failed-task views, and summary counts through TaskRepository.
- Stage 3 Step 6-I report task adapter: added a pure route adapter that converts legacy Anta Meituan daily report page parameters into TaskSubmitter-compatible REPORT_GENERATE payloads.
- Stage 3 Step 6-K report task feature flag: wired Anta Meituan daily reporting to `REPORT_TASK_MODE` with default `legacy` behavior and an opt-in local TaskSubmitter path.
- Stage 3 Step 6-L task result asset persistence: added ResultAssetService and wired ReportExecutor to save CSV result assets when Task payload includes an output folder.
- Stage 3 Step 6-M task result access layer: added TaskResultService to expose safe task result metadata and backend-only download information through TaskQueryService.
- Stage 3 Step 6-N task API layer: added authenticated HTTP APIs for task submission, safe result lookup, and result download through TaskSubmitter and TaskResultService.
- Stage 3 Step 6-O task status page: added `/tasks` and `/tasks/<task_id>` pages backed by TaskQueryService and TaskResultService, including status, errors, result summaries, and download links.
- Stage 3 Step 6-Q permission service MVP: added PermissionService and wired task list, task detail, task result API, task download API, and task submission API to session-user permission checks.
- Stage 3 Step 6-S task read model extension: expanded TaskReadModel with owner, brand, business unit, platform, channel, updated_at, scope_snapshot, and top-level result_asset from existing SQLite records without changing schema.
- Stage 3 Step 6-T task result read model adaptation: updated TaskResultService to prefer TaskReadModel.result_asset while preserving legacy task.result["result_asset"] fallback and existing safe download checks.
- Stage 7 Step 7-D PostgreSQL task repository skeleton: added PostgreSQL connection and TaskRepository adapter skeletons that implement the existing interface without opening real database connections or executing SQL.
- Production foundation Step 1 storage/assets boundary: froze storage.py as Legacy Adapter through STORAGE_MIGRATION_BOUNDARY.md, added ResultAssetService -> StorageProvider -> LocalStorageProvider, and decoupled ReportExecutor from local result paths while preserving CSV output payloads.
- Verification 2026-08-03: `python -m unittest discover -s tests -p "test_*.py"` ran 190 tests OK; `python -m py_compile` passed for Step 1 modified Python files.
- Step 7-E-1 ApplicationContainer skeleton: added process-level dependency assembly for CoreConfig, logger, SQLite repositories, services, result assets, executors, TaskRunner, and TaskSubmitter without wiring app.py or migrating business logic.
- Verification 2026-08-03: `python -m unittest discover -s tests -p "test_*.py"` ran 195 tests OK; `python -m py_compile backend\core\container.py tests\test_application_container.py intranet_app\app.py` passed; explicit imports for `intranet_app.app` and `backend.core.container` passed.
- Step 7-E-2 application bootstrap integration: added compatible `create_intranet_app()` startup helper, optional `ApplicationContainer` attachment on `IntranetApp`, and lifecycle `close()` handling while keeping direct legacy `IntranetApp(config)` construction available.
- Verification 2026-08-03: `python -m unittest discover -s tests -p "test_*.py"` ran 199 tests OK; `python -m py_compile intranet_app\app.py tests\test_application_bootstrap.py backend\core\container.py` passed; `create_intranet_app` import check passed.
- Step 7-E-3 container read-service resolution: migrated TaskQueryService, TaskResultService, and PermissionService resolvers to prefer `app.container.services` while preserving legacy SQLite fallback constructors.
- Verification 2026-08-03: `python -m unittest discover -s tests -p "test_*.py"` ran 203 tests OK; `python -m py_compile intranet_app\app.py tests\test_container_service_resolution.py` passed.
- Step 7-E-4 container TaskSubmitter resolution: exposed the existing in-process TaskSubmitter through `app.container.services.task_submitter`, updated `_task_submitter()` to prefer it, and preserved the legacy synchronous fallback path.
- Step 10-A Anta Meituan daily report Task migration: documented the legacy-vs-task execution path, validated `REPORT_TASK_MODE=task` through ReportTaskAdapter -> TaskSubmitter -> TaskRunner -> ReportExecutor -> ReportService -> ResultAssetService, and added regression tests for legacy parity, Task submission, CSV asset persistence, TaskResult download, and failed status recording.
- Verification 2026-08-03: `python -m unittest discover -s tests -p "test_*.py"` ran 206 tests OK; `python -m py_compile intranet_app\app.py backend\core\container.py tests\test_container_task_submitter_resolution.py` passed.

## Not Completed

- P2 currently supports first-phase Anta Kids + Meituan instant retail only.
- JD, Tmall, mini-program, official-site, and CRM data mappings are planned but not fully implemented in the foundation layer.
- Public/cloud deployment is not approved or production-hardened.
- Image generation is not yet wired into the formal P2 delivery flow.
- Brand profile management is still basic; structured brand-tone templates need to be connected to P2.
- Role-based permissions are lightweight and need hardening before shared production use.
- Backend core modules are available; `REPORT_TASK_MODE` is now wired into the Anta Meituan daily route, while most runtime settings still use legacy `intranet_app.config`.
- Repository adapters are available, but legacy `app.py` still calls `AppStorage` directly until service-layer migration begins.
- `DataFoundationService` is available for migration, but the legacy upload route still uses the original `app.py` flow until explicit wiring is approved.
- `ReportService` is available for migration, but the legacy report routes still use the original `app.py` flow until explicit wiring is approved.
- `AIService` and `AIContentService` are available for migration, but the legacy P2 routes still use the original `app.py` flow until explicit wiring is approved.
- `TaskService` is available as a future async entry boundary, but current web requests still execute synchronously until worker integration is approved.
- Worker contracts are defined for future async execution, but no background worker, broker, scheduler, or route wiring has been added.
- Local executor adapters are available for service-backed task execution, but web routes are not yet wired to submit work through them.
- TaskRunner is available for local dispatch, but web routes and automation pages still call legacy synchronous flows until explicit wiring is approved.
- TaskSubmitter is available as a Web/API submission entry; only the Anta Meituan daily route has an opt-in feature-flag path in this step.
- TaskQueryService is available for future management and monitoring pages, but no frontend route has been connected in this step.
- Anta Meituan daily reports have a tested `REPORT_TASK_MODE=task` migration path; weekly reports and other report routes still use legacy synchronous flows.

## Current Bugs And Risks

- Bailian may return HTTP 403 when the API key lacks model permission, account quota, or `qwen-plus` access.
- The browser plugin depends on the business user's logged-in platform session and cannot bypass CAPTCHA, MFA, or platform permission limits.
- If selected report dates are missing from the foundation layer, P1/P2 correctly fail closed and ask for plugin export/import.
- `ai_report_config_materials` contains real business data and large files; it must stay mostly local and ignored by Git.
- The local SQLite database is runtime state and must not be uploaded.
- Production health checks currently verify local configuration only; PostgreSQL, Redis, and worker checks still need implementation.
- SQLite repository adapters intentionally preserve the legacy storage behavior; full user creation, RBAC, and PostgreSQL implementations are still pending.
- Data foundation service preserves existing status and import rules, but it has not yet replaced the legacy route in production flow.
- Meituan monthly reporting is not foundation-backed yet; `ReportService` keeps that gap explicit instead of reading raw monthly source files.
- AI service retries are intentionally minimal in Step 5; production-grade rate limiting, request tracing, cost tracking, and async queue execution remain pending.
- Step 6-A stores task state transitions as existing automation run records because the current SQLite schema has no general task-run result table; richer payloads require a later schema migration.
- Step 6-B only validates JSON-compatible worker payloads and results; concrete executor implementations still need idempotency keys, progress events, locking, and timeout enforcement.
- Step 6-C executors convert JSON payloads into service requests, but they do not yet persist progress events or enforce distributed locks.
- Step 6-D runner maps task types to executors in-process only; cross-process queue semantics, worker retries, cancellation, and visibility timeouts remain future work.
- Step 6-E submission is still synchronous because Redis/Celery is not introduced yet; task submission metadata must be present in payload until web forms are explicitly adapted.
- Step 6-F derives current status from the latest existing automation run because no general async task table exists yet; richer progress history needs a later schema migration.
- Step 6-I only covers Anta Kids Meituan daily report payload conversion; weekly and multi-brand adapters still need separate contracts.
- Step 6-L saves CSV assets from ReportExecutor, but Task mode still lacks a legacy-compatible job download record and user-facing task status/download page.
- Step 6-M provides the backend access layer for Task assets, but no HTTP route or page button is wired to it yet.
- Step 6-N exposes task APIs through the local intranet app, but it still relies on the current session cookie and in-process execution until RBAC tokens and async workers are added.
- Step 6-O exposes a task status UI, but permissions are still based on the existing logged-in session rather than full RBAC scoping.
- Step 6-Q uses existing user role strings and task read fields only; formal brand-scope permissions still need future RBAC tables and task metadata fields in the read model.
- Step 6-S exposes task scope fields through the read model, but persistence still comes from legacy automation tables until the future PostgreSQL tasks/task_runs/task_results migration.
- Step 6-T keeps result assets backed by legacy run message JSON until the future task_results table exists; the service interface is now ready for the formal read model.
- Step 7-D PostgreSQL TaskRepository is a contract skeleton only; write methods intentionally fail closed until reviewed SQL and integration tests exist.
- Step 10-A Task mode for Anta Meituan daily reports is still synchronous and foundation-only; it does not create a legacy job record, so users must use Task result pages/API for task-mode downloads. Keep `REPORT_TASK_MODE=legacy` as the default until business acceptance confirms parity.
- Production foundation Step 1 keeps LocalStorageProvider as the only concrete asset provider; OSS/S3 support remains a later adapter and no database schema was changed.
- Step 7-E-1 container is not yet wired into `app.py`; it is a skeleton assembly boundary only, with PostgreSQL intentionally failing closed until a reviewed adapter exists.

## Next Plan

1. Confirm Bailian model permissions and switch to an available model if needed.
2. Complete Anta Meituan daily report date-selection flow with business validation.
3. Add structured brand profile templates to P2 and bind them to brand/channel selection.
4. Extend foundation mappings to JD, Tmall, mini-program, official site, and CRM.
5. Add admin-visible rule pages for data dictionary, field mapping, and import decisions.
6. Prepare an internal security review package before any public or company-wide deployment.
7. Add API auth hardening and RBAC-scoped task visibility before enabling `REPORT_TASK_MODE=task` for business users.
8. Extend TaskReadModel with brand, business unit, platform, and channel metadata during the later schema/read-model migration.
9. Implement Step 2 configuration environment split and production logging enhancements without changing business processors.
10. Gradually replace selected route-level dependency creation with `app.container.services` behind compatibility tests, starting with read-only task query/result services.

- Step 10-J-0 local Phase 1 Task mode setup: added local `.env` with only `REPORT_TASK_MODE=task` for Admin grey validation, documented local Task mode setup in `docs/LOCAL_TASK_MODE_SETUP.md`, and required `/console/environment` to show `task` before Phase 1 execution. No business code, processor, Task flow, or database schema was changed.
