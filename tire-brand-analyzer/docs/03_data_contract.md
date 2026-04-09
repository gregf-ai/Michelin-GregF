# Data Contract

## Source
ROIC.ai API (REST)

## Tickers
MGDDY, GT, BRDCY, CTTAY, PLLIF, SSUMY

## Endpoints Used
- /v2/company/profile/{ticker}
- /v2/company/news/{ticker} (limit=50, paged)
- /v2/company/earnings-calls/list/{ticker}
- /v2/company/earnings-calls/transcript/{ticker}
- /v2/fundamental/income-statement/{ticker} (annual, limit=15)
- /v2/fundamental/cash-flow/{ticker} (annual, limit=15)
- /v2/fundamental/ratios/profitability/{ticker} (annual, limit=15)
- /v2/stock-prices/{ticker} (limit=2520 where available)

## Storage Layout
- data/raw/profiles/{ticker}.json
- data/raw/news/{ticker}.json
- data/raw/transcripts/{ticker}.json
- data/raw/income_statements/{ticker}.json
- data/raw/cash_flows/{ticker}.json
- data/raw/ratios/{ticker}.json
- data/raw/stock_prices/{ticker}.json

## Currency Normalization Policy
- Income statement and cash flow monetary columns are normalized to USD in loader stage.
- Ratios are not converted (already unitless percentages).
- Annual-average FX maps used:
  - EURUSD by fiscal year
  - JPYUSD by fiscal year

## Known Data Gaps
- Sumitomo transcript coverage is unavailable from source endpoint.
- Price history length differs by ticker (for example PLLIF has fewer points than others).
- News volume differs materially by company.

## Data Freshness
- Snapshot-based; refreshed by running data/extract/download.py.

## Local Analytics Store (DuckDB)
- Build command: `python data/load/process_to_duckdb.py`
- Output file: `data/processed/curated/financial_analyst.duckdb`
- Full rebuild behavior: each run recreates the DuckDB file.
- Included tables:
  - Processed financials: `income_statements`, `cash_flows`, `ratios`, `stock_prices`
  - Raw text: `news_articles`, `transcripts`
  - Company data: `companies`, `profiles`
  - Summaries: `news_summaries`, `transcript_summaries`, `transcript_company_summaries`
