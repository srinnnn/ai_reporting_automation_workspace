# Visual Baseline Status

Current status:

- `VISUAL_REGRESSION = PARTIAL`
- `RUNTIME_VISUAL_BASELINE = PENDING_REACT_MIGRATION`

| Route | Baseline | Status |
| --- | --- | --- |
| `/` | `homepage.png` | SEEDED_REFERENCE_ONLY |
| `/workspace/ANTA` | pending | BASELINE_PENDING |
| `/workspace/ANTA/P1` | pending | BASELINE_PENDING |
| `/schedule` | pending | BASELINE_PENDING |

`homepage.png` is copied from the Product Owner approved design source. It is not a Playwright runtime screenshot and is not an operational visual regression gate. It must be validated, replaced, or confirmed against a real runtime screenshot from `http://127.0.0.1:8785/` during the future React/Vite migration task. This task does not implement the runtime migration.
