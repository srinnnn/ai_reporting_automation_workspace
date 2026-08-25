# Middle Platform V3 Migration

## Decision

Move the official runtime to React + Vite frontend served by FastAPI on port `8785`.

## Current State

- Current stage: MERGED
- Post-merge verification: PASS
- Release status: NOT_RELEASED
- Next stage: READY_FOR_NEXT_STAGE
- Evidence: PR #7, PR head `270fabd0fd7ac6a5b7f0da3e7e926b392aef8e8a`, merge commit `d703742296b54adcc766c8d6921c7fdae93560cc`, post-merge CI run `32723298005`, visual artifact `runtime-visual-homepage` / `9518608262`.

## Active Visual Enrichment

- Task: PLAT-V3-MICRO-UI-ICON-SYSTEM-ENRICHMENT-V1
- Branch: feature/plat-v3-micro-ui-icon-system-v1
- Status: READY_FOR_REVIEW
- Contract: Product IA from PR #9 remains unchanged; only icon-assisted visual hierarchy, status language, badges, and micro UI are in scope.
- Release: NOT_RELEASED

## Schedule State

- Development: COMPLETE
- Merge: COMPLETE
- Post-merge verification: COMPLETE
- Release: NOT_RELEASED

## Current Scope

- React routes for homepage, workspace, category, project, schedule, and platform modules
- FastAPI `/api/v1` contract
- Docker production runtime
- CI for backend, frontend, and Docker smoke
- runtime visual screenshot foundation

## Business Compatibility

Real business production compatibility is not required for this migration. Legacy business code is retained unless its server-rendered UI conflicts with the new production entry.
