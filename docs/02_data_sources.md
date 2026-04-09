# Data Sources

## Purpose
Document where data comes from, how complete it is, and how it is used in analysis.

## Primary Sources
- ROIC.ai REST API:
  - Company profiles
  - Income statements (annual)
  - Cash flows (annual)
  - Profitability ratios (annual)
  - Stock prices (daily)
  - News
  - Earnings call transcripts
- USPTO Open Data (patent analytics pipeline)

## Company Coverage
- Michelin (MGDDY)
- Goodyear (GT)
- Bridgestone (BRDCY)
- Continental (CTTAY)
- Pirelli (PLLIF)
- Sumitomo (SSUMY)

## Timeline Coverage
- Financials and ratios: up to 15 annual periods (metric-dependent)
- Dashboard comparisons: 10-year median + 2025 snapshot where available
- Stock prices: daily history, aggregated to annual metrics/candlesticks in app views
- News and transcripts: source-dependent; uneven by company
- Patent filings: source-dependent by ticker/company and filing availability

## Data Freshness and Reproducibility
- App runs on local snapshot data for deterministic demos.
- Refresh handled by ETL scripts in `data/extract`, `data/transform`, and `data/load`.

## Known Gaps
- Coverage differs by ticker and endpoint.
- Some transcript availability is sparse for select companies.
- Stock history length varies by listing and source availability.

## ETL Detail
For ETL folder structure, stage responsibilities, naming conventions, and operational rules,
see `data/README_ETL.md`.
