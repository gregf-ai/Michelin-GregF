# ETL Run Manifests

Store one manifest JSON file per ETL execution in `runs/manifests/`.

## Filename Convention

`<pipeline>_<YYYYMMDD_HHMMSS>.json`

Examples:
- `extract_roic_20260409_123015.json`
- `transform_patent_ai_20260409_130501.json`
- `load_financial_duckdb_20260409_131900.json`

## Required Fields

- `run_id`
- `pipeline`
- `stage` (`extract|transform|load`)
- `started_at_utc`
- `finished_at_utc`
- `status` (`success|failed`)
- `inputs` (list of paths/ids)
- `outputs` (list of paths)
- `row_counts` (object)
- `notes`

Use `manifests/TEMPLATE.json` as a starter.
