# Visual Baseline Status

Current status:

- `VISUAL_REGRESSION = READY`
- `RUNTIME_VISUAL_BASELINE = READY`

| Route | Baseline | Status |
| --- | --- | --- |
| `/` | `homepage.png` | SEEDED_REFERENCE_ONLY |
| `/` | `../runtime/homepage.png` | RUNTIME_SCREENSHOT_READY |
| `/workspace/ANTA` | pending | BASELINE_PENDING |
| `/workspace/ANTA/P1` | pending | BASELINE_PENDING |
| `/schedule` | pending | BASELINE_PENDING |

`homepage.png` is copied from the Product Owner approved design source. `tests/visual/runtime/homepage.png` is the Playwright runtime screenshot from `http://127.0.0.1:8785/`.
