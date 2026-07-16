# Data Quality Report — Notebook 1

- Raw rows: **10,000** -> Clean rows: **9,989** (quarantined: 10)
- Columns: 20 -> 18 (dropped 4 geo + created_at + creation_date raw; added tx_date, rep fields, outlier flag)

## Cleaning ledger

| step                    | rule                                                              |   rows_affected |
|:------------------------|:------------------------------------------------------------------|----------------:|
| drop_geo_columns        | dropped ['city', 'region', 'area', 'area_id'] (100% null)         |               0 |
| drop_created_at         | export timestamp, not a business event                            |               0 |
| quarantine_bad_dates    | creation_date = '0000-00-00'                                      |              10 |
| remove_non_transactions | quantity=0 AND amount=0                                           |               1 |
| normalize_whitespace    | trim + collapse spaces in 5 text cols                             |               0 |
| rep_fallback            | employee_name -> user_name when null                              |            3278 |
| flag_outliers           | robust z > 3.5 on log(amount), per supplier — FLAGGED not deleted |              50 |

## Per-supplier coverage

|   supplier_id | first_tx            | last_tx             |   rows |   span_days |
|--------------:|:--------------------|:--------------------|-------:|------------:|
|            59 | 2025-01-02 16:16:02 | 2026-06-04 11:12:03 |   1000 |         517 |
|            60 | 2024-12-01 00:01:05 | 2024-12-01 23:52:10 |   1000 |           0 |
|            63 | 2025-09-20 13:52:02 | 2026-04-25 11:33:05 |   1000 |         216 |
|            67 | 2025-08-26 00:55:16 | 2026-02-22 14:44:59 |   1000 |         180 |
|            69 | 2025-08-05 00:06:59 | 2025-08-06 02:51:06 |   1000 |           1 |
|            72 | 2025-01-08 18:15:20 | 2025-12-31 15:53:31 |    990 |         356 |
|            73 | 2024-11-15 18:24:24 | 2026-06-02 05:38:18 |   1000 |         563 |
|            75 | 2026-04-01 00:22:15 | 2026-06-03 18:41:57 |   1000 |          63 |
|            76 | 2022-07-07 13:50:41 | 2024-12-28 15:48:22 |   1000 |         905 |
|            80 | 2026-01-04 09:07:26 | 2026-05-14 10:04:56 |   1000 |         130 |
