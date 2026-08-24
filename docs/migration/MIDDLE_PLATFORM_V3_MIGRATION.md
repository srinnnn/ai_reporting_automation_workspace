# Middle Platform V3 Migration

## Decision

Move the official runtime to React + Vite frontend served by FastAPI on port `8785`.

## Current Scope

- React routes for homepage, workspace, category, project, schedule, and platform modules
- FastAPI `/api/v1` contract
- Docker production runtime
- CI for backend, frontend, and Docker smoke
- runtime visual screenshot foundation

## Business Compatibility

Real business production compatibility is not required for this migration. Legacy business code is retained unless its server-rendered UI conflicts with the new production entry.
