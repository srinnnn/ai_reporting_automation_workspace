# Report Task Production Acceptance

## Execution

- Execution date: 2026-08-03
- Scope: Anta Meituan daily report
- Date range: 20260715 to 20260725
- Runner: `scripts/report_consistency_runner.py`
- Output directory: `runtime/consistency_reports/`
- Report file: `runtime/consistency_reports/anta_meituan_daily_consistency_20260715_20260725.csv`

Command used:

```powershell
$env:PYTHONPATH='.;src'
py -3.12 scripts/report_consistency_runner.py --start-date 20260715 --end-date 20260725 --output-dir runtime/consistency_reports
```

## Acceptance Scope

The batch acceptance compared Legacy and Task mode for each daily report date.

Checked items:

- Legacy status
- Task status
- output row count difference
- amount difference
- core field difference
- CSV header consistency
- Task `result_asset` availability
- Task download information availability

## Result Summary

Overall result: FAIL

Reason: 5 dates failed because both Legacy and Task mode found no available completed order data in the foundation layer. The failure message is consistent across both modes, so the current evidence points to a data availability issue, not a Task migration difference.

Summary:

| Metric | Count |
| --- | ---: |
| Total dates | 11 |
| PASS dates | 6 |
| FAIL dates | 5 |
| Task-only failures | 0 |
| Legacy vs Task row deltas on PASS dates | 0 |
| Amount deltas on PASS dates | 0.00 |

## PASS Dates

| Date | Legacy Status | Task Status | Rows | Row Delta | Amount Delta | Asset / Download |
| --- | --- | --- | ---: | ---: | ---: | --- |
| 20260720 | success | success | 35 | 0 | 0.00 | PASS |
| 20260721 | success | success | 35 | 0 | 0.00 | PASS |
| 20260722 | success | success | 35 | 0 | 0.00 | PASS |
| 20260723 | success | success | 35 | 0 | 0.00 | PASS |
| 20260724 | success | success | 35 | 0 | 0.00 | PASS |
| 20260725 | success | success | 34 | 0 | 0.00 | PASS |

Interpretation:

- Legacy and Task mode produce matching rows for all PASS dates.
- Core comparison returned no field differences.
- Amount delta is 0.00 for every PASS date.
- Task result asset and download checks passed for every PASS date.

## FAIL Dates

| Date | Legacy Status | Task Status | Error Classification | Reason |
| --- | --- | --- | --- | --- |
| 20260715 | failed | failed | Data issue | `ValidationError: 商品/订单数据在当前日期范围内没有可用完成订单` |
| 20260716 | failed | failed | Data issue | `ValidationError: 商品/订单数据在当前日期范围内没有可用完成订单` |
| 20260717 | failed | failed | Data issue | `ValidationError: 商品/订单数据在当前日期范围内没有可用完成订单` |
| 20260718 | failed | failed | Data issue | `ValidationError: 商品/订单数据在当前日期范围内没有可用完成订单` |
| 20260719 | failed | failed | Data issue | `ValidationError: 商品/订单数据在当前日期范围内没有可用完成订单` |

Failure classification:

- Data issue: 5
- Task issue: 0
- Report issue: 0
- Asset issue: 0

## Risk Assessment

1. The Task implementation has passed result consistency checks for the dates with complete available data.
2. The 20260715-20260719 failures should not be treated as Task migration failures because Legacy and Task failed with the same validation error.
3. Formal rollout should not cover dates without complete foundation data unless business confirms those dates should be allowed to return empty/no-data reports.
4. Before switching shared usage to Task mode, the missing completed-order data for 20260715-20260719 should be confirmed with the business owner or corrected in the foundation layer.

## Acceptance Decision

Current decision: conditional pass for data-complete dates only.

Task mode can proceed to controlled business validation for Anta Meituan daily report if the rollout scope starts from dates with complete foundation data, such as 20260720-20260725.

Task mode should not be globally enabled for historical backfill until 20260715-20260719 data availability is resolved or explicitly accepted as no-data dates.

## Next Step

Recommended next step:

1. Ask business owner to confirm whether 20260715-20260719 should contain completed order data.
2. If data should exist, backfill the missing foundation data and rerun the batch consistency runner.
3. If those dates are confirmed as no-data dates, document the business explanation and continue Phase 2 designated business user validation.
4. Keep `REPORT_TASK_MODE=legacy` as the default until business validation is complete.
