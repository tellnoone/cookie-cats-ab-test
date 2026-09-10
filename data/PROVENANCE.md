# Data Provenance

**File:** `raw/cookie_cats.csv`
**Rows:** 90,189 (plus header)
**SHA-256:** `5ab54d761fbddcd50de7b88e4eaf7837cba4569474f50c043a4d17ee342c46bd`
**Retrieved:** 2026-09-10

## Source

The canonical Cookie Cats A/B test dataset (originally distributed by DataCamp;
widely mirrored on Kaggle). Retrieved from:

    https://raw.githubusercontent.com/robguilarr/ab_testing_cookie_cats/main/datasets/cookie_cats.csv

## Integrity check

The file was cross-checked against two further independent mirrors:

- `ryanschaub/Mobile-Games-A-B-Testing-with-Cookie-Cats` @ `master`
- `thegarrickchu/Mobile-Games-Ab-testing-with-Cookie-Cats` @ `master`

All three copies are **byte-identical** (same SHA-256, same 2,707,297-byte length).
Three unrelated uploads agreeing bit-for-bit is good evidence the file is the
unmodified original rather than one analyst's edited copy.

## Schema

| Column | Type | Meaning |
|---|---|---|
| `userid` | int | Unique player identifier |
| `version` | str | Arm: `gate_30` (control) or `gate_40` (treatment) |
| `sum_gamerounds` | int | Game rounds played in the first 14 days after install |
| `retention_1` | bool | Player returned 1 day after install |
| `retention_7` | bool | Player returned 7 days after install |

## Caveats

- A **finished snapshot**. No timestamps, no pre-period, no per-day series, so
  peeking/sequential-testing and CUPED cannot be demonstrated on it (see plan §7).
- No revenue or session fields, so the metric the gate most directly targets is
  unobservable here (see plan §2).
