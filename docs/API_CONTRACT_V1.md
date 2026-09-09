# API Contract V1

Base path: `/api/v1`

## Health

`GET /health`

Response: `{ "status": "ok" }`

## Readiness

`GET /ready`

Response fields:

- `status`: `ok` or `error`
- `runtime_directory`: boolean
- `database`: boolean
- `frontend_dist`: boolean
- `environment`: string

## Version

`GET /version`

Response fields: `version`, `commit_sha`, `build_time`, `environment`.

## Dashboard

`GET /dashboard`

Production empty response is valid when `DEMO_MODE=false`: `brands=[]`, `projects=[]`, KPI counts `0`.

## Brands

`GET /brands`

`GET /brands/{brand_key}`

Unknown brands return `404`.

## Projects

`GET /projects`

`GET /projects/{project_key}`

Unknown projects return `404`.

## Private Data Local Center Integration

`GET /integrations/private-data-local-center/health`

Returns `service`, `status` (`AVAILABLE` or `UNAVAILABLE`), `entry_path`, and `message`. An unavailable upstream is reported as `UNAVAILABLE`; it is not reported as connected.

The middle platform exposes only these collection-request proxy routes:

- `POST /collection-requests`
- `GET /collection-requests/{request_id}`
- `POST /collection-requests/{request_id}/draft`
- `POST /collection-requests/{request_id}/submit`

Request bodies and upstream HTTP status codes are preserved. An unreachable upstream returns `502`. Validation and persistence contracts remain owned by `private-data-local-center`.

The same-origin frontend entry is `/integrations/private-data-local-center/`. Only its root HTML and `/integrations/private-data-local-center/assets/*` are proxied. Other paths under that prefix return `404` and are never forwarded upstream.

## Platform Modules

`GET /schedules`, `/tasks`, `/reports`, `/data-foundation`

Routes must provide a stable empty state before real business data is connected.
