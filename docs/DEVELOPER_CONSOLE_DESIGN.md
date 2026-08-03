# Developer Console Architecture Design

## 1. Platform Positioning

Developer Console is not a pure operations page. It is the unified internal console for the AI business automation platform.

Its goal is to become the shared workspace for:

- business automation development
- task execution visibility
- deployment readiness checks
- environment and configuration visibility
- future data foundation and AI operation management

Target users:

| User | Primary Need |
| --- | --- |
| Developer | Inspect tasks, system status, errors, environment readiness, and future execution chains. |
| Business Owner | View business task status, generated results, and future brand/data coverage. |
| System Admin | View all system status, configuration status, task status, logs, deployment information, and operational risks. |

The console must stay behind existing authentication and permission checks. It must not bypass Service Layer boundaries.

## 2. Current Capability Inventory

| Area | Existing Capability | Current File / Service | Console Usage |
| --- | --- | --- | --- |
| Dependency assembly | `ApplicationContainer` | `backend/core/container.py` | Resolve shared services without rebuilding dependencies per request. |
| Task read model | `TaskQueryService` | `backend/services/task_query_service.py` | Task list, task detail, task summary, failed task list. |
| Task result access | `TaskResultService` | `backend/services/task_result_service.py` | Safe result metadata and download information. |
| Permission | `PermissionService` | `backend/services/permission_service.py` | Role and task visibility checks. |
| Health checks | Health functions | `backend/core/health.py` | System, database, filesystem, AI configuration status. |
| Config | Core config | `backend/core/config.py` | Sanitized config status. Never expose secrets. |
| Deployment readiness | Preflight script | `scripts/preflight_check.py` | Future deployment readiness summary. |
| Docker baseline | Docker files | `Dockerfile`, `docker-compose.yml`, `.env.example` | Future environment center and deployment docs. |

## 3. Page Architecture Design

### 3.1 Dashboard

Purpose: provide a first-screen operational overview for the platform.

Display:

- system running status
- task statistics
- AI status
- storage status
- recent failed tasks

Recommended widgets:

| Widget | Fields | Data Source |
| --- | --- | --- |
| System Status | overall status, database status, filesystem status, AI config status | `backend/core/health.py` |
| Task Summary | total, pending, running, success, failed | `TaskQueryService.get_task_summary()` |
| AI Status | provider, model, api key configured status | `ApplicationContainer.config.ai` |
| Storage Status | runtime/upload/result/log directory readiness | `backend/core/health.py` |
| Recent Failed Tasks | task_id, task_type, created_by, error summary, updated_at | `TaskQueryService.list_failed_tasks()` |

Rules:

- Dashboard must only show sanitized configuration.
- No secret value, API key, token, cookie, or password can be displayed.
- Task rows must be filtered by `PermissionService` for non-admin users.

### 3.2 Task Center

Purpose: manage and inspect task execution state based on existing Task Framework.

Current read-only fields:

- `task_id`
- `task_type`
- `status`
- `created_by`
- created time
- updated time
- execution result
- error message
- result asset / download availability

Future actions:

- retry task
- rerun task
- view execution chain
- compare old and new task result
- inspect input payload snapshot

Data sources:

- `TaskQueryService.list_tasks()`
- `TaskQueryService.get_task(task_id)`
- `TaskResultService.get_result(task_id)`
- `TaskResultService.get_download_info(task_id)`
- `PermissionService.can_view_task()`
- `PermissionService.can_download_task()`

Rules:

- Current stage is read-only.
- Retry/rerun must wait until async task model and idempotency rules are ready.
- Download must use `TaskResultService`; no controller may construct filesystem paths directly.

### 3.3 Environment Center

Purpose: display deployment and runtime configuration status in a safe, read-only way.

Read-only examples:

- `APP_ENV`
- `DATABASE_BACKEND`
- `REPORT_TASK_MODE`
- `AI_PROVIDER`
- AI model
- AI key configured status only
- Storage Provider
- runtime directory status
- upload/result/log directory status

Rules:

- The page must not directly edit `.env`.
- The page must not show secret values.
- Production configuration changes must go through server environment variables, Secret manager, or a controlled admin process.

Data sources:

- `ApplicationContainer.config`
- `backend/core/config.py`
- `backend/core/health.py`
- future preflight wrapper service

### 3.4 Data Center

Purpose: future operating center for data intake and foundation data quality.

Future display:

- uploaded file status
- file recognition status
- data foundation import status
- validation report
- brand/platform/channel mapping
- data version
- data coverage by date
- failed validation rows

Future data sources:

- Data foundation Service Layer
- FoundationRepository
- validation report read model
- source file metadata

Rules:

- Formal report/P2 outputs must still read from the unified foundation data layer.
- Raw uploads are intake artifacts only.
- Console must not generate reports directly from raw files.

### 3.5 AI Center

Purpose: future operating center for AI generation traceability and quality control.

Future display:

- AI run records
- prompt version
- model provider and model name
- token usage
- latency
- input/output hash
- failure reason
- content quality status

Future data sources:

- planned `ai_runs` repository/read model
- `AIService`
- `AIContentService`

Rules:

- Do not store or display full secrets.
- Prompt content should be scoped by permission and may require redaction.
- Token/cost data should be aggregated for managers.

### 3.6 Developer Operations

Purpose: provide developer-facing operational visibility.

Future display:

- logs
- CI status
- current deployed version
- Docker image version
- Git commit SHA
- deployment environment
- preflight status
- runtime warnings

Future data sources:

- structured logs
- CI provider API or imported CI metadata
- deployment metadata file generated by CI
- `scripts/preflight_check.py` through a wrapper service

Rules:

- Logs must be paginated and redacted.
- Viewer role should not access logs or full system metadata.

## 4. Backend API Design

All APIs must call Service Layer through `ApplicationContainer`. Controllers must not instantiate business services manually and must not call `storage.py` directly.

### 4.1 `GET /api/system/health`

Purpose: return sanitized system health.

Data source:

- `backend/core/health.py`

Response shape:

```json
{
  "status": "ok",
  "components": [
    {
      "name": "database",
      "status": "ok",
      "message": "database is reachable"
    }
  ]
}
```

### 4.2 `GET /api/system/config/status`

Purpose: return sanitized configuration status.

Data source:

- `ApplicationContainer.config`
- `backend/core/config.py`

Response shape:

```json
{
  "environment": "development",
  "database_backend": "sqlite",
  "report_task_mode": "legacy",
  "ai": {
    "provider": "bailian",
    "model": "qwen-plus",
    "api_key_configured": false
  },
  "storage": {
    "runtime_configured": true,
    "upload_configured": true,
    "result_configured": true,
    "log_configured": true
  }
}
```

### 4.3 `GET /api/tasks`

Purpose: return visible task list.

Query parameters:

- `task_type`
- `status`
- `created_by`
- `brand_id`
- `business_unit`
- `platform`
- `channel`

Data source:

- `TaskQueryService.list_tasks()`
- `PermissionService.filter_visible_tasks()`

### 4.4 `GET /api/tasks/<task_id>`

Purpose: return safe task detail.

Data source:

- `TaskQueryService.get_task(task_id)`
- `TaskResultService.get_result(task_id)`
- `PermissionService.can_view_task(user, task)`

### 4.5 `GET /api/tasks/<task_id>/download`

Purpose: download task result asset safely.

Data source:

- `TaskResultService.get_download_info(task_id)`
- `PermissionService.can_download_task(user, task)`

Rules:

- API must not expose absolute runtime paths.
- API must fail closed when task is missing or permission check fails.
- API must not read files outside ResultAssetService/TaskResultService boundaries.

## 5. Permission Design

Roles:

| Role | System Status | Task View | Result Download | Logs | Environment Center |
| --- | --- | --- | --- | --- | --- |
| Admin | All | All | All allowed successful task assets | Yes | Yes |
| Developer | Yes | System and task metadata | Configurable, default same as task visibility | Yes, redacted | Yes, sanitized |
| Business Owner | Limited business-safe status | Own brand/business scope | Own visible successful task assets | No | No |
| Viewer | No system details | Own visible business tasks only | Own visible successful task assets if allowed | No | No |

Permission rules:

- Task list must call `PermissionService.filter_visible_tasks()`.
- Task detail must call `PermissionService.can_view_task()`.
- Download must call `PermissionService.can_download_task()` and then `TaskResultService.get_download_info()`.
- System config APIs are Admin/Developer only.
- Logs are Admin/Developer only and must be redacted.

## 6. Architecture Relationship

Required architecture:

```text
Developer Console
        ↓
API Layer / Controller
        ↓
ApplicationContainer
        ↓
Service Layer
        ↓
Repository Layer
        ↓
Database / Storage Adapter
```

Rules:

- Controller must not directly create Service instances.
- Controller must not call `storage.py`.
- Controller must not directly query SQLite.
- Controller must not directly scan runtime result files.
- Service dependencies must be explicitly assembled by `ApplicationContainer`.

Allowed flow example:

```text
GET /api/tasks
        ↓
app.container.services.task_query_service
        ↓
TaskQueryService
        ↓
TaskRepository
```

Forbidden flow example:

```text
GET /api/tasks
        ↓
AppStorage / storage.py
        ↓
SQLite
```

## 7. Future Extension Roadmap

### 7.1 PostgreSQL

Future goal:

- replace SQLite adapter with PostgreSQL adapter behind Repository interfaces.
- support multi-user concurrency and production query performance.

Current stage:

- design only.
- no PostgreSQL runtime code is introduced by this document.

### 7.2 Redis

Future goal:

- provide queue broker and transient task coordination.

Current stage:

- not implemented.
- task execution remains synchronous.

### 7.3 Celery

Future goal:

- run data import, report generation, and AI content generation outside HTTP request threads.

Current stage:

- not implemented.
- existing Worker Framework remains local/synchronous.

### 7.4 OSS / Object Storage

Future goal:

- move result assets from local runtime storage to OSS/S3-compatible object storage.

Current stage:

- local ResultAssetService and LocalStorageProvider remain the active implementation.

### 7.5 CI/CD

Future goal:

- expose latest CI status, tested commit SHA, Docker image tag, and deployment version.

Current stage:

- CI exists for tests and py_compile.
- Console only designs future display.

## 8. Future Development Order

Recommended implementation sequence:

1. Add read-only system APIs: `/api/system/health`, `/api/system/config/status`.
2. Add read-only task list/detail API improvements through existing Task services.
3. Apply PermissionService checks consistently to all console APIs.
4. Add minimal Developer Console dashboard page.
5. Add Task Center page.
6. Add Environment Center page.
7. Add Data Center read model after foundation metadata is stabilized.
8. Add AI Center after `ai_runs` read model is designed and implemented.
9. Add Developer Operations after structured logging and deployment metadata exist.

## 9. Current-Step Restrictions

Step 9-A is design-only.

Do not modify:

- `app.py`
- Service implementations
- Repository implementations
- processors
- database schema
- Task execution flow

Do not add:

- PostgreSQL code
- Redis
- Celery
- frontend page code

The Developer Console must start as a read-only operational surface and expand only after Service/Repository boundaries are stable.