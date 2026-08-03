# Contributing Guide

This project is an internal AI business automation platform. Changes must protect existing daily report, weekly report, data foundation, task, and AI content flows.

## 1. Development Environment

Recommended local environment:

- Windows development machine or Ubuntu server-compatible environment
- Python 3.12+, aligned with the enterprise deployment baseline
- PowerShell for local Windows commands
- Git and GitHub Desktop for source control

The application must continue to support the legacy local startup command:

```powershell
python -m intranet_app.app
```

## 2. Install Dependencies

Install runtime and development dependencies from the repository root:

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```

`requirements.txt` contains runtime dependencies only.
`requirements-dev.txt` includes runtime dependencies plus development tools.

Do not use `pip freeze` to overwrite dependency files. Add only dependencies that are actually used by the project.

## 3. Local Startup

Start the intranet workbench from the repository root:

```powershell
$env:PYTHONPATH='.;src'
python -m intranet_app.app
```

Default local URL:

```text
http://127.0.0.1:8785
```

The legacy launcher should remain usable when present:

```powershell
.\start_intranet_workbench.bat
```

## 4. Run Tests

Run the full regression suite before submitting changes:

```powershell
$env:PYTHONPATH='.;src;C:\Users\JM042403\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages'
python -m unittest discover -s tests -p "test_*.py"
```

Expected current baseline:

```text
213 tests OK
```

Test warnings that are intentionally asserted by failure-path tests are acceptable only when the suite ends with `OK`.

## 5. py_compile Check

Run Python compilation checks from the repository root:

```powershell
$files = git ls-files "*.py"
if ($files) { python -m py_compile @files }
```

This catches syntax errors without modifying files.

## 6. Black, Ruff, and Mypy

Configuration lives in `pyproject.toml`.

Current usage policy:

- Black is configured but must not be run as an automatic mass format step without approval.
- Ruff is configured for lint detection. Do not run `ruff --fix` unless the task explicitly allows code edits.
- Mypy is configured in compatibility mode. It is not yet a blocking production gate.

Manual checks may be run locally:

```powershell
python -m black --check .
python -m ruff check .
python -m mypy
```

Do not mix formatting-only changes with business logic changes in the same commit.

## 7. Git Commit Rules

Keep commits small and scoped.

Recommended commit types:

- `docs:` documentation-only changes
- `test:` test-only changes
- `chore:` configuration or tooling changes
- `refactor:` structure changes without business behavior changes
- `fix:` bug fixes
- `feat:` new user-facing or platform capability

Before committing, verify:

```powershell
git status --short
```

Do not commit unrelated local changes or real business data.

## 8. Prohibited Commit Content

Never commit secrets or real business files.

Forbidden examples:

- `.env`
- API keys
- passwords
- tokens
- cookies
- platform account credentials
- real business Excel files
- real business CSV files
- Meituan, JD, Tmall, mini-program, official-site, or CRM exports
- `runtime/` data
- `outputs/`
- `uploads/`
- `downloads/`
- logs
- local SQLite databases

Sensitive project material directories must remain local unless files are clearly templates, examples, or documentation.

## 9. Business Logic Protection

Do not change processor calculation logic, report output fields, prompt rules, or database schema unless the task explicitly requires it.

Formal P1 and P2 outputs must read from the unified foundation data layer. Raw downloaded or uploaded files are intake artifacts only.