# Codex Development Rules

## Project Structure

- `intranet_app/`: Python intranet workbench, storage layer, routes, processors, static CSS, and runtime configuration.
- `intranet_app/processors/`: P1/P2/P3 processing modules.
- `browser_extensions/meituan_download_assistant/`: Chrome extension for assisting Meituan report downloads.
- `tools/`: local synchronization and utility scripts.
- `tests/`: unit tests for data foundation, reporting, automation, P2 content, and UI layout.
- `data/examples/`: desensitized sample data that may be committed.
- `data/templates/`: Excel or CSV templates that may be committed.
- `data/local/`: real local business data. Do not commit.
- `ai_report_config_materials/`: local business material package. Treat raw and manual data inside it as sensitive unless a file is clearly a template or README.

## Startup

Local workbench:

```powershell
python -m intranet_app.app
```

Default URL:

```text
http://127.0.0.1:8785
```

Common launcher:

```powershell
.\start_intranet_workbench.bat
```

AI API configuration is local-only:

```text
http://127.0.0.1:8785/admin/ai-settings
```

## Test Command

Use this exact command from the repository root:

```powershell
$env:PYTHONPATH='.;src;C:\Users\JM042403\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages'; python -m unittest discover -s tests -p "test_*.py"
```

## Mandatory Data Path

All P1 reports, including daily, weekly, and monthly reports, and all P2 AI capabilities, including AI selection, audience strategy, selling-point extraction, copywriting, and image generation, must read from the unified foundation data layer.

Raw downloaded or uploaded CSV, XLS, and XLSX files are intake artifacts only. They may be synchronized, archived, recognized, mapped, cleaned, and validated, but they must not be used directly to generate formal reports or AI outputs.

Required path:

1. Plugin or business user provides raw files.
2. Files enter `intake`.
3. The data foundation center performs file recognition, field mapping, cleaning, validation, and brand ownership checks.
4. Passed records are written to unified foundation tables such as `fact_order_product`, `fact_store_finance`, `fact_store_traffic`, and `fact_service_review`.
5. P1 and P2 modules query the foundation tables by `brand_id`, `platform`, `channel`, and date.

Formal P1/P2 entry points must fail closed when required foundation data is missing. Do not silently fall back to scanning `Downloads`, `runtime/intake`, or uploaded raw files for a formal output.

Raw-file readers may exist only for intake, validation, migration, backfill, tests, or explicit diagnostic tools. They must not be wired to production report buttons.

## Directories That Must Not Be Committed

Do not add or commit files from:

- `data/local/`
- `intranet_app/runtime/`
- `outputs/`
- `uploads/`
- `downloads/`
- `logs/`
- `node_modules/`
- `ai_report_config_materials/**/01_raw_data/`
- `ai_report_config_materials/**/02_manual_deliverables/`
- real Meituan, JD, Tmall, mini-program, official-site, or CRM exports.

## Editing Rules

- Preserve user business files. Do not delete or move real data unless the user explicitly asks.
- Use `apply_patch` for manual source edits.
- Keep generated outputs out of Git.
- Never store API keys, cookies, passwords, or platform account credentials in code, Excel, CSV, or docs.
- If a report or AI output requires missing foundation data, raise a clear validation error instead of fabricating data.
