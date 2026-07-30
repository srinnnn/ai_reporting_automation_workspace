# GitHub Upload Cleanup Report

Generated on 2026-07-30.

## 1. Files Larger Than 50MB

All files larger than 50MB are real business data or local Git/Codex internal objects. The working-tree business files are ignored by `.gitignore`.

| Size | File |
| ---: | --- |
| 340.22 MB | `ai_report_config_materials/03_config_automation_materials/03-1_anta_instant_retail/03-1-1_listing_filter/2026-07-13_092154.csv` |
| 339.14 MB | `ai_report_config_materials/01_data_processing/01-3_weekly_report/anta_weekly_report/02_manual_deliverables/anta_weekly_materials/2026_07_weekly_reports/week1/2026-07-06_092021.csv` |
| 189.80 MB | `ai_report_config_materials/01_data_processing/01-3_weekly_report/anta_weekly_report/02_manual_deliverables/anta_weekly_materials/2026_07_weekly_reports/week1/0706_-2026-07-06_092021.xlsx` |
| 182.31 MB | `ai_report_config_materials/01_data_processing/01-3_weekly_report/anta_weekly_report/01_raw_data/2026_07_week2/product_export_2026-07-13_092154.xlsx` |
| 166.41 MB | `ai_report_config_materials/01_data_processing/01-3_weekly_report/anta_weekly_report/02_manual_deliverables/anta_weekly_materials/2026_06_weekly_reports/0629/2026-06-29_091307.csv` |
| 91.61 MB | `ai_report_config_materials/01_data_processing/01-3_weekly_report/anta_weekly_report/02_manual_deliverables/anta_weekly_materials/2026_06_weekly_reports/0615_-2026-06-15_092138_1.xlsx` |
| 90.96 MB | `ai_report_config_materials/01_data_processing/01-3_weekly_report/anta_weekly_report/02_manual_deliverables/anta_weekly_materials/2026_06_weekly_reports/0629/0629_-2026-06-29_091307.xlsx` |
| 90.38 MB | `ai_report_config_materials/01_data_processing/01-3_weekly_report/anta_weekly_report/02_manual_deliverables/anta_weekly_materials/2026_06_weekly_reports/0622/0622_-2026-06-22_095553_1.xlsx` |
| 70.47 MB | `ai_report_config_materials/01_data_processing/01-3_weekly_report/anta_weekly_report/02_manual_deliverables/anta_weekly_materials/2026_06_weekly_reports/2026-06-15_112746.csv` |

Verification result: no working-tree file larger than 50MB remains unignored.

## 2. Real Business Data

Treat these as local-only:

- `ai_report_config_materials/**/01_raw_data/**`
- `ai_report_config_materials/**/02_manual_deliverables/**`
- `ai_report_config_materials/**/03_unresolved/**`
- `ai_report_config_materials/**/meituan_auto_download/**`
- `ai_report_config_materials/**/jd_export/**`
- `ai_report_config_materials/**/tmall_export/**`
- `intranet_app/runtime/**`
- root Excel workbooks such as `内容任务耗时统计.xlsx` and development planning workbooks
- real `.csv`, `.xls`, `.xlsx`, `.xlsm`, `.xlsb`, `.docx`, `.pptx`, archives, local databases, logs, and generated reports

## 3. Runtime-Required Files To Keep

Keep and upload:

- `intranet_app/**/*.py`
- `intranet_app/static/style.css`
- `intranet_app/README.md`
- `intranet_app/samples/**` because these are small desensitized test samples
- `browser_extensions/meituan_download_assistant/**`
- `tools/*.py`, `tools/*.ps1`, `tools/*.mjs`
- `tests/test_*.py`
- root launcher `.bat` files
- `.gitattributes`
- `.gitignore`
- `README.md`
- `AGENTS.md`
- `PROJECT_STATUS.md`
- `data/README.md`
- `data/examples/**`
- `data/templates/**`
- explicitly named Excel templates under `ai_report_config_materials`

## 4. Regenerable Files

Do not upload:

- `intranet_app/runtime/**`
- `outputs/**`
- `uploads/**`
- `downloads/**`
- `logs/**`
- `__pycache__/**`
- `*.pyc`
- `node_modules/**`
- `.pytest_cache/**`
- local SQLite database files
- generated archive indexes and data dictionaries

## 5. Removed From Git Tracking

No large files were removed with `git rm --cached` because this repository currently has no tracked files:

```text
git ls-files
```

returned an empty list before cleanup.

Local Codex snapshot refs under `refs/codex/turn-diffs/**` were removed and Git object storage was pruned. This did not delete working-tree files.

## 6. Data Directory Convention

```text
data/
├── examples/
│   └── desensitized test data
├── templates/
│   └── Excel or CSV templates
└── local/
    └── real local business data, ignored by Git
```

## 7. Current Git Status Summary

Expected files to add:

- code: `intranet_app/`, `browser_extensions/`, `tools/`
- tests: `tests/`
- docs/rules: `README.md`, `PROJECT_STATUS.md`, `AGENTS.md`, `GITHUB_UPLOAD_CLEANUP_REPORT.md`
- safe data scaffolding: `data/`
- templates: small template files under `ai_report_config_materials`

Ignored examples:

- `intranet_app/runtime/`
- `node_modules/`
- `outputs/`
- root business Excel files
- large Anta/Meituan CSV and Excel files
- local database files

## 8. .gitignore Content

```gitignore
# Python cache and tooling
__pycache__/
*.py[cod]
*$py.class
.pytest_cache/
.mypy_cache/
.ruff_cache/
.coverage
.coverage.*
htmlcov/
.hypothesis/

# Virtual environments and local secrets
.env
.env.*
!.env.example
.venv/
venv/
env/
ENV/
local_settings.py
*.pem
*.key
*.p12
*.pfx

# Node and frontend artifacts
node_modules/
**/node_modules/
dist/
build/
coverage/
.cache/

# Runtime/generated local state
runtime/
**/runtime/
intranet_app/runtime/
outputs/
uploads/
downloads/
Downloads/
logs/
*.log
*.tmp
*.temp
*.bak

# Local databases
*.db
*.sqlite
*.sqlite3
*.sqlite3-*
db.sqlite3
db.sqlite3-journal

# Raw business data and platform exports
*.csv
*.xls
*.xlsx
*.xlsm
*.xlsb
*.parquet
*.ndjson
*.jsonl
*.zip
*.7z
*.rar
*.tar
*.gz
*.exe
*.msi
*.dmg
*.pkg

# Local installers/tools downloaded on this machine
local_tools/keepass_installer/**

# Office/business documents likely to contain real client data
*.docx
*.doc
*.pptx
*.ppt
ecco_*.png
ECCO_*.svg
~$*

# Business material folders: keep structure/docs, exclude raw/manual data files
ai_report_config_materials/**/01_raw_data/**
ai_report_config_materials/**/02_manual_deliverables/**
ai_report_config_materials/**/03_unresolved/**
ai_report_config_materials/**/meituan_auto_download/**
ai_report_config_materials/**/jd_export/**
ai_report_config_materials/**/tmall_export/**

# Local data convention
data/local/**
!data/local/
!data/local/README.md

# Keep source code, docs, test-safe examples, and templates
!.gitattributes
!.gitignore
!README.md
!PROJECT_STATUS.md
!AGENTS.md
!intranet_app/README.md
!intranet_app/samples/
!intranet_app/samples/**
!data/
!data/README.md
!data/examples/
!data/examples/**
!data/templates/
!data/templates/**
!ai_report_config_materials/**/*template*.xlsx
!ai_report_config_materials/**/*Template*.xlsx
!ai_report_config_materials/**/*模板*.xlsx
!ai_report_config_materials/**/README.md
!ai_report_config_materials/**/.gitkeep

# System/editor files
.DS_Store
Thumbs.db
desktop.ini
.vscode/
.idea/
.cursorignore
.cursorindexingignore
```

## 9. Next GitHub Upload Steps

1. Review GitHub Desktop changes. Confirm ignored large files do not appear in the file list.
2. Stage only source, docs, tests, templates, and desensitized examples.
3. Commit locally with a message such as `Prepare repository for private GitHub upload`.
4. Create a private GitHub repository.
5. Push the local commit to the private repository.
6. After pushing, confirm GitHub file browser contains code/templates/tests/docs only and no real exports.
