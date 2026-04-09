"""Materialize processed and raw datasets into a local DuckDB database.

Scope (simplified):
- Processed CSV: income statements, cash flows, ratios, stock prices
- Processed CSV summaries: news/transcript summaries
- Raw JSON: profiles, news, transcripts

Usage:
    c:/Michelin-GregF/.venv/Scripts/python.exe data/load/process_to_duckdb.py
    c:/Michelin-GregF/.venv/Scripts/python.exe data/load/process_to_duckdb.py --db-path data/processed/curated/financial_analyst.duckdb
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = DATA_ROOT / "raw"
PROCESSED_DIR = DATA_ROOT / "processed"
CURATED_DIR = PROCESSED_DIR / "curated"
ANALYTICS_DIR = PROCESSED_DIR / "analytics"

TICKER_TO_COMPANY = {
    "MGDDY": "Michelin",
    "GT": "Goodyear",
    "BRDCY": "Bridgestone",
    "CTTAY": "Continental",
    "PLLIF": "Pirelli",
    "SSUMY": "Sumitomo",
}


def _read_json(path: Path) -> Any:
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _create_or_replace_table(conn: duckdb.DuckDBPyConnection, name: str, df: pd.DataFrame) -> int:
    if df is None:
        df = pd.DataFrame()
    conn.register("tmp_df", df)
    conn.execute(f"CREATE OR REPLACE TABLE {name} AS SELECT * FROM tmp_df")
    conn.unregister("tmp_df")
    return len(df)


def _load_csv(path: Path, parse_dates: list[str] | None = None) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, parse_dates=parse_dates or [])


def _build_companies_df() -> pd.DataFrame:
    rows = []
    for ticker, company in TICKER_TO_COMPANY.items():
        rows.append({"ticker": ticker, "company": company})
    return pd.DataFrame(rows)


def _build_profiles_df() -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for ticker, company in TICKER_TO_COMPANY.items():
        data = _read_json(RAW_DIR / "profiles" / f"{ticker}.json")
        if not isinstance(data, list) or not data:
            continue
        profile = data[0] if isinstance(data[0], dict) else {}
        row = {"ticker": ticker, "company": company}
        row.update(profile)
        rows.append(row)

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    # Keep one row per ticker in case of accidental duplicates.
    df = df.drop_duplicates(subset=["ticker"], keep="last")
    return df


def _build_news_articles_df() -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for ticker, company in TICKER_TO_COMPANY.items():
        data = _read_json(RAW_DIR / "news" / f"{ticker}.json")
        if not isinstance(data, list):
            continue
        for article in data:
            if not isinstance(article, dict):
                continue
            rows.append(
                {
                    "ticker": ticker,
                    "company": company,
                    "published_date": article.get("published_date"),
                    "title": article.get("title"),
                    "article_url": article.get("article_url"),
                    "article_text": article.get("article_text"),
                    "site": article.get("site"),
                }
            )

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df["published_date"] = pd.to_datetime(df["published_date"], errors="coerce")
    df = df.drop_duplicates(subset=["ticker", "published_date", "title"], keep="last")
    return df


def _build_transcripts_df() -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for ticker, company in TICKER_TO_COMPANY.items():
        data = _read_json(RAW_DIR / "transcripts" / f"{ticker}.json")
        if not isinstance(data, list):
            continue
        for t in data:
            if not isinstance(t, dict):
                continue
            rows.append(
                {
                    "ticker": ticker,
                    "company": company,
                    "symbol": t.get("symbol"),
                    "year": t.get("year"),
                    "quarter": t.get("quarter"),
                    "date": t.get("date"),
                    "content": t.get("content"),
                }
            )

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df["quarter"] = pd.to_numeric(df["quarter"], errors="coerce")
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.drop_duplicates(subset=["ticker", "year", "quarter"], keep="last")
    return df


def sync_transcripts_table(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = duckdb.connect(str(db_path))
    transcripts_df = _build_transcripts_df()

    if transcripts_df.empty:
        print("No transcript rows found in raw JSON files. Nothing to sync.")
        conn.close()
        return

    existing_tables = {row[0] for row in conn.execute("SHOW TABLES").fetchall()}
    if "transcripts" not in existing_tables:
        count = _create_or_replace_table(conn, "transcripts", transcripts_df)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_transcripts_ticker_period ON transcripts(ticker, year, quarter)")
        conn.close()
        print(f"Created transcripts table with {count} rows at: {db_path}")
        return

    before_count = conn.execute("SELECT COUNT(*) FROM transcripts").fetchone()[0]
    conn.register("tmp_transcripts_source", transcripts_df)
    conn.execute("CREATE OR REPLACE TEMP TABLE tmp_transcripts_pending AS SELECT * FROM tmp_transcripts_source")
    conn.unregister("tmp_transcripts_source")

    pending_count = conn.execute("SELECT COUNT(*) FROM tmp_transcripts_pending").fetchone()[0]
    update_count = conn.execute(
        """
        SELECT COUNT(*)
        FROM tmp_transcripts_pending pending
        JOIN transcripts existing
          ON existing.ticker IS NOT DISTINCT FROM pending.ticker
         AND existing.year IS NOT DISTINCT FROM pending.year
         AND existing.quarter IS NOT DISTINCT FROM pending.quarter
        WHERE existing.symbol IS DISTINCT FROM pending.symbol
           OR existing.date IS DISTINCT FROM pending.date
           OR existing.content IS DISTINCT FROM pending.content
           OR existing.company IS DISTINCT FROM pending.company
        """
    ).fetchone()[0]
    conn.execute(
        """
        UPDATE transcripts AS existing
        SET symbol = pending.symbol,
            date = pending.date,
            content = pending.content,
            company = pending.company
        FROM tmp_transcripts_pending AS pending
        WHERE existing.ticker IS NOT DISTINCT FROM pending.ticker
          AND existing.year IS NOT DISTINCT FROM pending.year
          AND existing.quarter IS NOT DISTINCT FROM pending.quarter
        """
    )
    conn.execute(
        """
        DELETE FROM tmp_transcripts_pending pending
        USING transcripts existing
        WHERE existing.ticker IS NOT DISTINCT FROM pending.ticker
          AND existing.year IS NOT DISTINCT FROM pending.year
          AND existing.quarter IS NOT DISTINCT FROM pending.quarter
        """
    )
    insert_count = conn.execute("SELECT COUNT(*) FROM tmp_transcripts_pending").fetchone()[0]

    if insert_count:
        conn.execute("INSERT INTO transcripts BY NAME SELECT * FROM tmp_transcripts_pending")

    conn.execute("CREATE INDEX IF NOT EXISTS idx_transcripts_ticker_period ON transcripts(ticker, year, quarter)")
    after_count = conn.execute("SELECT COUNT(*) FROM transcripts").fetchone()[0]
    conn.close()

    print(f"Transcript sync complete for: {db_path}")
    print(f"  - source transcript rows: {pending_count}")
    print(f"  - updated existing rows: {update_count}")
    print(f"  - inserted new rows: {insert_count}")
    print(f"  - total rows after sync: {after_count} (was {before_count})")


def build_duckdb(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # Full rebuild mode.
    if db_path.exists():
        db_path.unlink()

    conn = duckdb.connect(str(db_path))

    table_counts: dict[str, int] = {}

    # Dimension tables.
    table_counts["companies"] = _create_or_replace_table(conn, "companies", _build_companies_df())
    table_counts["profiles"] = _create_or_replace_table(conn, "profiles", _build_profiles_df())

    # Processed financial datasets.
    table_counts["income_statements"] = _create_or_replace_table(
        conn,
        "income_statements",
        _load_csv(CURATED_DIR / "income_statements_usd.csv", parse_dates=["date"]),
    )
    table_counts["cash_flows"] = _create_or_replace_table(
        conn,
        "cash_flows",
        _load_csv(CURATED_DIR / "cash_flows_usd.csv", parse_dates=["date"]),
    )
    table_counts["ratios"] = _create_or_replace_table(
        conn,
        "ratios",
        _load_csv(CURATED_DIR / "ratios.csv", parse_dates=["date"]),
    )
    table_counts["stock_prices"] = _create_or_replace_table(
        conn,
        "stock_prices",
        _load_csv(CURATED_DIR / "stock_prices.csv", parse_dates=["date"]),
    )

    # Raw text datasets.
    table_counts["news_articles"] = _create_or_replace_table(conn, "news_articles", _build_news_articles_df())
    table_counts["transcripts"] = _create_or_replace_table(conn, "transcripts", _build_transcripts_df())

    # Processed summary datasets.
    table_counts["news_summaries"] = _create_or_replace_table(
        conn,
        "news_summaries",
        _load_csv(ANALYTICS_DIR / "news_summaries_ollama.csv", parse_dates=["date_start", "date_end"]),
    )
    table_counts["transcript_summaries"] = _create_or_replace_table(
        conn,
        "transcript_summaries",
        _load_csv(ANALYTICS_DIR / "transcript_summaries_ollama.csv", parse_dates=["date"]),
    )
    table_counts["transcript_company_summaries"] = _create_or_replace_table(
        conn,
        "transcript_company_summaries",
        _load_csv(ANALYTICS_DIR / "transcript_company_summaries_ollama.csv"),
    )

    # Helpful indexes for common filters.
    conn.execute("CREATE INDEX IF NOT EXISTS idx_income_ticker_year ON income_statements(ticker, fiscal_year)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_cash_ticker_year ON cash_flows(ticker, fiscal_year)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ratios_ticker_year ON ratios(ticker, fiscal_year)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_prices_ticker_date ON stock_prices(ticker, date)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_news_ticker_date ON news_articles(ticker, published_date)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_transcripts_ticker_period ON transcripts(ticker, year, quarter)")

    conn.close()

    print(f"DuckDB rebuilt at: {db_path}")
    for table_name, count in table_counts.items():
        print(f"  - {table_name}: {count} rows")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build DuckDB from processed and raw datasets")
    parser.add_argument(
        "--db-path",
        default=str(CURATED_DIR / "financial_analyst.duckdb"),
        help="Path to output DuckDB file",
    )
    parser.add_argument(
        "--sync-transcripts-only",
        action="store_true",
        help="Append only new raw transcript rows into the existing DuckDB transcripts table.",
    )
    args = parser.parse_args()
    if args.sync_transcripts_only:
        sync_transcripts_table(Path(args.db_path))
        return
    build_duckdb(Path(args.db_path))


if __name__ == "__main__":
    main()
