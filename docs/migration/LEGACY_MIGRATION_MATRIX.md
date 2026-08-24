# Legacy Migration Matrix

| Area | Status | Notes |
| --- | --- | --- |
| `intranet_app.app` server-rendered main UI | OBSOLETE_FOR_MAIN_ENTRY | Replaced by FastAPI serving React in Docker. |
| `intranet_app/processors` | RETAINED_BUSINESS_MODULE | Business code retained. |
| `backend/services` | MIGRATED | Reused as backend service layer where available. |
| Task/result services | RETAINED_BUSINESS_MODULE | Existing tests remain active. |
| External workbook UI dependencies | UNKNOWN | Not used by new React runtime; old tests now use explicit fixtures. |

`LEGACY_MAIN_UI_DEPENDENCY = 0` for production Docker entry.
