# Visual Baseline Status

Current status:

- `STRUCTURAL_VISUAL_REGRESSION = READY`
- `VISUAL_REGRESSION = PARTIAL`
- `RUNTIME_VISUAL_BASELINE = PENDING_SCREENSHOT_COMPARISON`

| Route | Baseline | Status |
| --- | --- | --- |
| `/` | `homepage.png` | SEEDED_REFERENCE_ONLY |
| `/` | `homepage-structure.json` | STRUCTURAL_REGRESSION_READY |
| `/` | `../runtime/homepage-global.png` | RUNTIME_SCREENSHOT_EVIDENCE |
| `/` Workspace Entry ANTA | `../runtime/homepage-workspace-entry-anta.png` | RUNTIME_SCREENSHOT_EVIDENCE |
| `/` Workspace Entry ECCO | `../runtime/homepage-workspace-entry-ecco.png` | RUNTIME_SCREENSHOT_EVIDENCE |
| `/workspace/ANTA` | `../runtime/workspace-anta.png` | RUNTIME_SCREENSHOT_EVIDENCE |
| `/workspace/ECCO` | `../runtime/workspace-ecco.png` | RUNTIME_SCREENSHOT_EVIDENCE |
| `/workspace/BSH` | `../runtime/workspace-bsh.png` | RUNTIME_SCREENSHOT_EVIDENCE |
| `/workspace/ANTA` | pending | BASELINE_PENDING |
| `/workspace/ANTA/P1` | pending | BASELINE_PENDING |
| `/schedule` | pending | BASELINE_PENDING |

`homepage.png` is copied from the Product Owner approved design source. `homepage-structure.json` is the operational Playwright comparison contract for the locked homepage structure. Files under `tests/visual/runtime/` are Playwright visual evidence from `http://127.0.0.1:8785/` at `1440x1000`, not screenshot-diff baselines.
