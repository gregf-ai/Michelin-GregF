# Data ETL Directory Structure

This document defines the target ETL layout for this repository.

## Goals
- Keep raw, intermediate, and final data clearly separated.
- Keep reproducible outputs in stable locations.
- Keep temporary logs/backups out of active analytical paths.
- Make every stage easy to rerun independently.

## Recommended Layout

```
data/
  README_ETL.md
  extract/
    download.py
    download_uspto_odp_filings.py
  transform/
    parse_manual_transcripts.py
    summarize_with_ollama.py
    summarize_uspto_patents_with_ollama.py
  load/
    process_to_csv.py
    process_to_duckdb.py
  raw/
    cash_flows/
    income_statements/
    news/
    profiles/
    ratios/
    stock_prices/
    transcripts/
    uspto_odp/
  intermediate/
    (optional staging outputs, deduped jsonl, cleaned tables)
  processed/
    curated/
      (published app-facing outputs)
    analytics/
      (exploratory and AI-analysis outputs)
  runs/
    manifests/
      (one json manifest per ETL run)
  archive/
    logs/
    backups/
```

## Stage Responsibilities

- extract:
  - Pull data from APIs/filesystems.
  - Write only to `raw/`.
  - Never overwrite `processed/` directly.

- transform:
  - Parse, clean, deduplicate, classify/summarize.
  - Read from `raw/` or `intermediate/`.
  - Write to `intermediate/` first when possible.

- load:
  - Build final analytical tables/DBs for the app.
  - Write primarily to `processed/curated/`.

## Naming Conventions

- Raw snapshots:
  - `<source>_<entity>_<YYYYMMDD>.jsonl` for time-partitioned runs.
  - If maintaining latest-only files, keep a single canonical filename and archive old files by run date.

- Processed outputs:
  - `<domain>_<grain>_<tool>.csv`
  - Example: `patent_ai_company_stats.csv`

- Run manifests:
  - `runs/manifests/<pipeline>_<YYYYMMDD_HHMMSS>.json`
  - Include: run_id, pipeline, started_at, finished_at, inputs, outputs, row_counts, status.

- Databases:
  - `<domain>_analyst.duckdb`

## Operational Rules

- Keep `raw/` append-only where possible.
- Use deterministic dedupe keys per domain:
  - USPTO filings: `(ticker, application_number)`.
- Keep logs and backups under `archive/`, not under `processed/` or `raw/` active folders.
- Publish only validated artifacts to `processed/`.

## Current Cleanup Applied

- Moved runtime logs from `processed/` to `archive/logs/`.
- Moved `.bak` files from active USPTO ticker folders to `archive/backups/uspto_odp/...`.
- Added ignore rules for archive/log files in `.gitignore`.
- ETL scripts were moved into `extract/`, `transform/`, and `load/`.
- Removed backward-compatible wrapper scripts from `data/` root.
- Removed duplicate root-level outputs from `processed/`.

## Suggested Next Refactor (Optional)

- Add manifest writing to each ETL script at start/end of run.
