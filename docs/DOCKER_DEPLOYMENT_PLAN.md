# Docker Deployment Plan

## 1. Current Docker Architecture

Step 8-A and Step 8-B prepare a local Docker runtime for the existing application.

Current container layout:

```text
Docker Compose
└── app
    ├── Python 3.12 runtime
    ├── intranet_app local web service
    ├── SQLite under mounted runtime directory
    └── synchronous Task framework
```

The app service starts with:

```bash
python -m intranet_app.app
```

Required local runtime assumptions:

- `INTRANET_HOST=0.0.0.0` inside the container so the mapped port is reachable.
- `INTRANET_ADMIN_PASSWORD` must be provided from `.env` and must not use the local default.
- `INTRANET_SECRET_KEY` must be provided from `.env` and must not use the local default.
- Runtime state is mounted at `./intranet_app/runtime:/app/intranet_app/runtime`.

## 2. Environment Variables

Use `.env.example` as the template. Copy it to `.env` for local Docker runs and fill only local values.

In production, do not upload `.env` to Git or image builds. Configure secrets through the cloud server environment variable manager or Secret manager.

| Variable | Purpose | Required | Example format |
| --- | --- | --- | --- |
| `APP_ENV` | Runtime environment name. Valid values are `development`, `testing`, `production`. | Yes | `development` |
| `APP_DEBUG` | Enables debug behavior when set to true-like values. Keep false in Docker. | No | `false` |
| `INTRANET_HOST` | Bind host for the web server. Docker uses all interfaces inside the container. | Yes | `0.0.0.0` |
| `INTRANET_PORT` | Web server port. | Yes | `8785` |
| `INTRANET_ADMIN_PASSWORD` | Initial admin password. Must be strong when host is not localhost. | Yes | `set-in-secret-manager` |
| `INTRANET_SECRET_KEY` | Session signing secret. Must be long and random. | Yes | `set-in-secret-manager` |
| `DATABASE_BACKEND` | Active database adapter. Current Docker baseline is SQLite only. | Yes | `sqlite` |
| `DATABASE_URL` | Future PostgreSQL DSN. Leave empty in Step 8-B. | No | empty |
| `SQLITE_PATH` | SQLite database path inside the container. | Yes | `/app/intranet_app/runtime/intranet.sqlite3` |
| `RUNTIME_DIR` | Runtime root directory. | Yes | `/app/intranet_app/runtime` |
| `UPLOAD_DIR` | Upload storage directory. | Yes | `/app/intranet_app/runtime/uploads` |
| `RESULT_DIR` | Generated result directory. | Yes | `/app/intranet_app/runtime/results` |
| `LOG_DIR` | Log directory. | Yes | `/app/intranet_app/runtime/logs` |
| `TEMPLATE_ROOT` | Local template and material root. | Yes | `/app/ai_report_config_materials` |
| `REPORT_TASK_MODE` | Report task feature flag. Keep `legacy` unless validating task mode. | Yes | `legacy` |
| `AI_PROVIDER` | AI provider name for configuration display and service checks. | No | `bailian` |
| `BAILIAN_BASE_URL` | Bailian-compatible API base URL. Not a secret. | No | `https://dashscope.aliyuncs.com/compatible-mode/v1` |
| `BAILIAN_MODEL` | Default Bailian model name. | No | `qwen-plus` |
| `DASHSCOPE_API_KEY` | Bailian API key. Leave empty unless AI features are enabled. | No | `set-in-secret-manager` |
| `ANTA_RETAIL_HOST` | Optional Anta retail launcher host. Not used by the main Docker app. | No | `127.0.0.1` |
| `ANTA_RETAIL_PORT` | Optional Anta retail launcher port. | No | `8766` |
| `ANTA_RETAIL_PROJECT_ROOT` | Optional Anta retail local project root. | No | empty |

## 3. Future Production Architecture

The intended production architecture is:

```text
Nginx / Ingress
        |
        v
Web App Container
        |
        +--> PostgreSQL
        |
        +--> Redis
        |
        +--> Worker Container
```

Future roles:

- Web: HTTP pages and APIs only.
- PostgreSQL: multi-user production database and task read model.
- Redis: task queue broker and transient coordination state.
- Worker: Excel processing, report generation, and AI generation outside the request thread.

## 4. Why PostgreSQL, Redis, and Celery Are Not Added Now

They are intentionally excluded from Step 8-A and Step 8-B.

PostgreSQL is not added because the project still runs on SQLite and the PostgreSQL repository adapters are not production-connected yet.

Redis is not added because Task execution remains synchronous. Adding Redis now would introduce infrastructure without changing runtime behavior.

Celery is not added because Worker contracts and local executors exist, but route migration and async state persistence are not complete.

This keeps the Docker foundation low risk and preserves all existing legacy flows.

## 5. Cloud Server Migration Path

Recommended migration sequence:

1. Build and run the current app-only Docker image locally.
2. Verify login, dashboard, task pages, daily report generation, and P2 content pages against non-sensitive test data.
3. Move runtime configuration into `.env` for local development and into cloud-managed environment variables or Secrets for production.
4. Add PostgreSQL only after the PostgreSQL repository adapter is implemented and tested.
5. Add Redis and Celery only after TaskSubmitter and TaskRunner are switched to asynchronous execution behind a feature flag.
6. Add Nginx or cloud load balancer after app health checks and static asset routing are stable.
7. Run 20-user concurrency tests before exposing the service to broader internal users.

## 6. Local Docker Commands

Create a local `.env` file from the template:

```bash
cp .env.example .env
```

Fill at least:

```text
INTRANET_ADMIN_PASSWORD=<strong-local-password>
INTRANET_SECRET_KEY=<long-random-secret>
REPORT_TASK_MODE=legacy
```

Start locally:

```bash
docker compose up --build
```

Open:

```text
http://127.0.0.1:8785
```

Stop:

```bash
docker compose down
```

## 7. Boundaries

Step 8-B does not change:

- business calculation logic
- processors
- services
- repositories
- database schema
- task status flow
- AI prompt logic

Raw business data, runtime files, generated outputs, `.env`, Excel files, and CSV files must stay out of the Docker build context and out of Git.