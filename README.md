# AI Reporting Automation Workspace

Local intranet workbench for reporting automation, data foundation validation, Meituan/JD-style platform data processing, and P2 AI content production.

## What Is In Git

- Python application code in `intranet_app/`
- Chrome extension code in `browser_extensions/`
- Utility scripts in `tools/`
- Unit tests in `tests/`
- Project rules in `AGENTS.md`
- Status notes in `PROJECT_STATUS.md`
- Desensitized examples and templates under `data/`
- Small Excel templates explicitly named as templates

## What Is Not In Git

Real business data is local-only and ignored by `.gitignore`, including:

- Meituan/JD/Tmall exports
- Anta daily, weekly, and monthly raw data
- Runtime uploads and generated reports
- Local SQLite databases
- API keys, cookies, passwords, and account credentials

## Development Environment

- Python 3.12+
- Install dependencies with `python -m pip install -r requirements-dev.txt`

## Start Locally

```powershell
python -m intranet_app.app
```

Open:

```text
http://127.0.0.1:8785
```

## Run Tests

```powershell
$env:PYTHONPATH='.;src;C:\Users\JM042403\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages'; python -m unittest discover -s tests -p "test_*.py"
```
