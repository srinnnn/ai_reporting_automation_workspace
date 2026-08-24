# Middle Platform V3 Architecture

## Runtime

Browser -> React production dist -> `/api/v1` -> FastAPI -> Service -> Repository / Adapter -> SQLite.

Production entry is `http://127.0.0.1:8785`.

FastAPI serves:

- `/api/v1/*` API routes
- `/assets/*` built React assets
- all other paths as SPA routes from `frontend/dist/index.html`

## Source of Truth

- Visual source: `docs/ui-reference/homepage-approved.html` and `docs/ui-reference/homepage-approved.png`
- Design tokens: `design-system/tokens.css`
- Motion tokens: `design-system/motion.ts`
- API contract: `docs/API_CONTRACT_V1.md`
- Runtime data: backend services and repositories

Production default is `DEMO_MODE=false`. Without real connected data, API responses must return empty state, `0`, or `NOT_CONNECTED`.

## Current Production Path

GitHub -> GitHub Actions CI -> trusted main commit -> self-hosted Windows runner -> versioned Windows release -> Uvicorn -> FastAPI -> React production dist -> `127.0.0.1:8785` -> existing Cloudflare Tunnel.

Production must not use the Vite dev server, `python -m intranet_app.app`, or `BaseHTTPRequestHandler`.

## Legacy Boundary

Legacy business code remains in `intranet_app/` for retained modules. Legacy server-rendered UI is no longer the production runtime entry after this migration.
