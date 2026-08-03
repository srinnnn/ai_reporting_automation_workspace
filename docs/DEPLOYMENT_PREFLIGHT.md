# Deployment Preflight Check

`scripts/preflight_check.py` provides a deployment preflight check for local Docker and future cloud server deployment.

It is intentionally standalone. It does not start the application, change business logic, modify the database, or create runtime directories.

## What It Checks

1. Required production environment variables:

- `INTRANET_SECRET_KEY`
- `INTRANET_ADMIN_PASSWORD`

These are blocking errors only when `APP_ENV=production`.

2. Runtime directories:

- `RUNTIME_DIR`
- `UPLOAD_DIR`
- `RESULT_DIR`
- `LOG_DIR`

Each directory must exist and be writable.

3. Configuration safety:

- empty secret key
- unsafe default secret key
- empty admin password
- unsafe default admin password
- short secret/admin values in production or non-localhost deployment

4. AI configuration:

When `AI_PROVIDER` is enabled, missing `DASHSCOPE_API_KEY` is reported as a warning, not a blocking error. This allows non-AI reporting and data workflows to start.

## Local Docker Usage

Create a local `.env` from the template:

```powershell
Copy-Item .env.example .env
```

Fill at least:

```text
INTRANET_ADMIN_PASSWORD=<strong-local-password>
INTRANET_SECRET_KEY=<long-random-secret>
```

Create runtime directories if they do not already exist:

```powershell
New-Item -ItemType Directory -Force -Path intranet_app\runtime\uploads,intranet_app\runtime\results,intranet_app\runtime\logs | Out-Null
```

Run the check:

```powershell
py -3.12 scripts\preflight_check.py --env-file .env --root .
```

Then start Docker:

```powershell
docker compose up --build
```

## Cloud Server Usage

On a cloud server, configure production variables through the cloud environment manager or Secret manager. Do not upload `.env` files containing secrets.

Example command after environment variables are configured:

```bash
python scripts/preflight_check.py --root /app
```

For production, use:

```text
APP_ENV=production
INTRANET_HOST=0.0.0.0
INTRANET_PORT=8785
INTRANET_ADMIN_PASSWORD=<secret-manager-value>
INTRANET_SECRET_KEY=<secret-manager-value>
DATABASE_BACKEND=sqlite
REPORT_TASK_MODE=legacy
```

Current Step 8-C still uses SQLite and synchronous tasks. PostgreSQL, Redis, and Celery are not part of this step.

## Exit Codes

- `0`: no blocking errors. Warnings may still be printed.
- `1`: blocking deployment error exists.

## Security Notes

The preflight output does not print secret values. It only reports whether required values are configured and whether they appear unsafe.

Never commit:

- `.env`
- API keys
- passwords
- tokens
- real business Excel or CSV files
- runtime data
- outputs/uploads/downloads