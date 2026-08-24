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

## Platform Modules

`GET /schedules`, `/tasks`, `/reports`, `/data-foundation`

Routes must provide a stable empty state before real business data is connected.
