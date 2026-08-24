# Visual Regression Foundation

This directory establishes the partial Middle Platform visual regression foundation.

Current status:

- `VISUAL_REGRESSION = PARTIAL`
- `RUNTIME_VISUAL_BASELINE = PENDING_REACT_MIGRATION`

## Baseline Routes

- `/` -> `tests/visual/baseline/homepage.png`
- `/workspace/ANTA` -> `BASELINE_PENDING`
- `/workspace/ANTA/P1` -> `BASELINE_PENDING`
- `/schedule` -> `BASELINE_PENDING`

## Source Layers

- Product design source: `docs/ui-reference/homepage-approved.png`
- Seeded reference only: `tests/visual/baseline/homepage.png`

The initial homepage image is seeded from the Product Owner approved screenshot because the React/Vite runtime migration has not been implemented in this task. It is `SEEDED REFERENCE ONLY`, not an operational runtime regression baseline. Future migration work must replace or confirm it with an automated Playwright screenshot from `http://127.0.0.1:8785/` after the approved UI is implemented.

## Gate

Do not report `VISUAL_REGRESSION = READY` from this seeded reference alone. Once a real runtime baseline exists, future key UI changes must compare baseline screenshots against runtime screenshots. Unapproved changes to module order, sidebar type, brand selector semantics, banner position, P1-P4 placement, visual language, or broad color usage fail the visual regression gate.
