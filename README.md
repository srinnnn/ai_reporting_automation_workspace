# AI Reporting Automation Workspace

Local intranet workbench for reporting automation, data foundation validation, Meituan/JD-style platform data processing, and P2 AI content production.

## What Is In Git

- Python application code in `intranet_app/`
- Chrome extension code in `browser_extensions/`
- Utility scripts in `tools/`
- Unit tests in `tests/`
- Project rules in `AGENTS.md`
- Status notes in `PROJECT_STATUS.md`
- Desensitized examples and templates under `data/`
- Small Excel templates explicitly named as templates

## What Is Not In Git

Real business data is local-only and ignored by `.gitignore`, including:

- Meituan/JD/Tmall exports
- Anta daily, weekly, and monthly raw data
- Runtime uploads and generated reports
- Local SQLite databases
- API keys, cookies, passwords, and account credentials

## Development Environment

- Python 3.12+
- Install dependencies with `python -m pip install -r requirements-dev.txt`
- Node.js 20.19+ for frontend CI parity

## Middle Platform V3 Runtime

Technology stack:

- React + TypeScript + Vite frontend in `frontend/`
- FastAPI backend in `backend/main.py`
- SQLite runtime storage, PostgreSQL-ready service boundary
- Windows native Uvicorn production runtime
- Docker multi-stage image retained for future approved infrastructure

Production entry:

```text
http://127.0.0.1:8785
```

Production default:

```text
DEMO_MODE=false
```

Without connected production data, the V3 API returns empty state, `0`, or `NOT_CONNECTED`.

## Start FastAPI

```powershell
uvicorn backend.main:app --host 127.0.0.1 --port 8785
```

## Start React Development Server

```powershell
cd frontend
npm ci
npm run dev
```

Vite runs on `127.0.0.1:5173` and proxies `/api` to `127.0.0.1:8785`.

## Docker

Docker Desktop / Docker Engine is not required on the current production workstation. Corporate IT policy makes the local Docker host unavailable:

```text
LOCAL_DOCKER_HOST=UNAVAILABLE_BY_CORPORATE_POLICY
```

Docker remains validated on GitHub-hosted Linux runners as a future deployment artifact.

Production on the current Windows host uses:

```powershell
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8785
```

through the versioned release scripts in `ops/windows-native/`.

Optional Docker runtime for approved hosts:

```powershell
docker compose up -d --build
```

Health checks:

```powershell
Invoke-WebRequest http://127.0.0.1:8785/api/v1/health
Invoke-WebRequest http://127.0.0.1:8785/api/v1/ready
Invoke-WebRequest http://127.0.0.1:8785/api/v1/version
```

## Run Tests

```powershell
$env:PYTHONPATH='.'; python -m unittest discover -s tests -p "test_*.py"
```

Frontend:

```powershell
cd frontend
npm run typecheck
npm run lint
npm run test
npm run build
npm audit --audit-level=moderate
```

## CI / GHCR / Deployment / Rollback

- PR CI runs backend unittest, Python compile, frontend typecheck/lint/unit/build/audit, e2e/visual, secret scan, and remote Docker smoke.
- GHCR image publication remains `FUTURE_READY`; package-write publishing needs explicit Product Owner approval for the target registry.
- Windows self-hosted deployment requires labels: `self-hosted`, `windows`, `x64`, `middle-platform-prod-native`.
- Native rollback selects an existing versioned release directory and must pass `/api/v1/health`, `/api/v1/ready`, and `/api/v1/version`.

See:

- `docs/ARCHITECTURE.md`
- `docs/API_CONTRACT_V1.md`
- `docs/DEPLOYMENT.md`
- `docs/ROLLBACK.md`
- `docs/SELF_HOSTED_RUNNER.md`
- `docs/DOCKER_CUTOVER.md`
