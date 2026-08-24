# Deployment

## Production Runtime

The current production workstation runs Windows native Uvicorn:

```text
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8785
```

Vite `5173`, `python -m intranet_app.app`, and `BaseHTTPRequestHandler` are not production entries.

## Versioned Windows Release Root

Production release root:

```text
C:\MiddlePlatformDeploy
```

Stable runtime data root:

```text
C:\MiddlePlatformData
```

Each release is deployed to:

```text
C:\MiddlePlatformDeploy\releases\<commit-sha>
```

The deployment scripts never overwrite the only working release directory.

## Native Launchers

```powershell
.\ops\windows-native\start-current.ps1
.\ops\windows-native\stop-current.ps1
.\ops\windows-native\restart-current.ps1
.\ops\windows-native\health-check.ps1
```

`start-current.ps1` reads `current-release.txt`, validates the release directory and `.venv`, starts only `backend.main:app`, writes `runtime-state.json`, and logs to `C:\MiddlePlatformDeploy\logs`.

## Deployment Workflow

`.github/workflows/deploy.yml` is manual-only and runs only on:

```text
self-hosted, windows, x64, middle-platform-prod-native
```

It rejects any `target_sha` that is not reachable from `origin/main`.

## Local Docker

Local Docker is unavailable by corporate policy and is not an application blocker:

```text
LOCAL_DOCKER_HOST=UNAVAILABLE_BY_CORPORATE_POLICY
```

Docker build/smoke validation runs remotely on GitHub-hosted Linux runners.

## GHCR

GHCR is a future deployment artifact. Image build/smoke validation is present, but external registry publication is not enabled until Product Owner explicitly authorizes package-write publication to the target GHCR namespace.

## Self-hosted Runner

Required labels:

- `self-hosted`
- `windows`
- `x64`
- `middle-platform-prod-native`

Runner registration token is external and must never be committed or pasted into logs.
