# Unified Data Foundation Rules

This file records the fixed data path for P1 reporting and P2 AI selection/content generation.

## Core Rule

Raw files are archived only. P1, P2, P3, and P4 must read from the unified foundation tables, not directly from uploaded CSV or Excel files.

Mandatory enforcement:

- Formal P1 outputs, including daily reports, weekly reports, monthly reports, and metric analysis, must query the foundation tables.
- Formal P2 outputs, including AI selection, audience strategy, selling-point extraction, copywriting, brief generation, and image generation, must query the foundation tables and approved brand/material libraries.
- Plugin downloads and manual uploads are intake sources only. They are not report sources.
- If the required foundation records do not exist for the requested brand, platform, channel, and date range, the system must stop and ask for data foundation ingestion. It must not fall back to raw CSV or Excel files.
- Any diagnostic or backfill script that reads raw files directly must be labeled as diagnostic/backfill and must not be connected to formal business report buttons.

## Processing Path

1. Business user uploads the raw file.
2. The upload form records business unit, brand, platform, channel, project, file type, and date range.
3. The system creates an `import_batch_id`.
4. The file is recognized by headers.
5. Raw fields are mapped to standard fields.
6. Rows are cleaned: tabs removed, text trimmed, empty values handled, money fields parsed as Decimal-compatible text.
7. Required fields and value types are validated.
8. Brand ownership is scored by store library, product library, platform, and date range.
9. Only validated data can enter the foundation tables.
10. AI generation can only use fields already present in the foundation tables.

## SQLite Control Tables

- `import_batches`
- `source_files`
- `field_mapping_rules`
- `validation_reports`
- `missing_data_items`

## SQLite Foundation Tables

- `fact_order_product`
- `fact_store_finance`
- `fact_store_traffic`
- `fact_service_review`
- `dim_product`
- `dim_store`
- `target_plan`
- `dim_campaign`
- `dim_platform_shop`
- `dim_channel_product`

## Platform And Channel Rule

The system distinguishes every source with both `platform` and `channel`.

Platforms:

- `meituan`
- `jd`
- `tmall`
- `mini_program`
- `official_site`

Channels:

- `instant_retail`
- `ecommerce`
- `private_domain`
- `official_direct`

Examples:

- Meituan Flash Sale: `platform=meituan`, `channel=instant_retail`
- JD: `platform=jd`, `channel=ecommerce`
- Tmall: `platform=tmall`, `channel=ecommerce`
- Mini Program: `platform=mini_program`, `channel=private_domain`
- Official Site: `platform=official_site`, `channel=official_direct`

## Brand Score Rule

- Store match: 40 points
- Product match: 40 points
- Platform match: 10 points
- Date range valid: 10 points

Decision:

- `>= 90`: auto pass
- `70-89`: manual review
- `< 70`: reject

## AI Rule

If product facts, stock status, selling points, campaign benefits, or brand rules are missing, the AI module must mark the item as pending business input. It must not invent missing facts.
