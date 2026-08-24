# Visual Regression Baseline

This directory establishes the Middle Platform visual regression foundation.

## Baseline Routes

- `/` -> `tests/visual/baseline/homepage.png`
- `/workspace/ANTA` -> `BASELINE_PENDING`
- `/workspace/ANTA/P1` -> `BASELINE_PENDING`
- `/schedule` -> `BASELINE_PENDING`

## Source Layers

- Product design reference: `docs/ui-reference/homepage-approved.png`
- Runtime regression baseline: `tests/visual/baseline/homepage.png`

The initial homepage baseline is seeded from the Product Owner approved screenshot because the React/Vite runtime migration has not been implemented in this task. Future migration work must replace or confirm it with an automated runtime screenshot after the approved UI is implemented.

## Gate

Future key UI changes must compare baseline screenshots against runtime screenshots. Unapproved changes to module order, sidebar type, brand selector semantics, banner position, P1-P4 placement, visual language, or broad color usage fail the visual regression gate.
