"""LangChain tools that the LangGraph agent can call to query financial data."""

from pathlib import Path
import re

import duckdb
import pandas as pd
from langchain_core.tools import tool

from src.data_loader import (
    COMPANY_NAMES,
    TICKERS,
    load_income_statements,
    load_cash_flows,
    load_ratios,
    load_stock_prices,
    load_profiles,
    load_all_transcripts,
    load_all_news,
    load_ai_patent_summaries,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DUCKDB_PATH = PROJECT_ROOT / "data" / "processed" / "curated" / "financial_analyst.duckdb"
MAX_SQL_ROWS = 200

ALLOWED_TABLES = {
    "companies",
    "profiles",
    "income_statements",
    "cash_flows",
    "ratios",
    "stock_prices",
    "news_articles",
    "transcripts",
    "news_summaries",
    "transcript_summaries",
    "transcript_company_summaries",
}


def _resolve_ticker(name: str) -> str | None:
    """Resolve a company name or ticker to a canonical ticker."""
    name_upper = name.upper().strip()
    if name_upper in TICKERS:
        return name_upper
    for t, n in COMPANY_NAMES.items():
        if n.upper() == name_upper:
            return t
    # Allow partial company-name matches for user convenience.
    for t, n in COMPANY_NAMES.items():
        if name_upper in n.upper() or n.upper() in name_upper:
            return t
    return None


def _fmt_number(val) -> str:
    if val is None:
        return "N/A"
    try:
        val = float(val)
    except (TypeError, ValueError):
        return str(val)
    if abs(val) >= 1e9:
        return f"${val/1e9:,.2f}B"
    if abs(val) >= 1e6:
        return f"${val/1e6:,.1f}M"
    if abs(val) >= 1e3:
        return f"${val/1e3:,.1f}K"
    return f"{val:,.2f}"


def _safe_pct(val) -> str:
    try:
        if val is None or pd.isna(val):
            return "N/A"
        return f"{float(val):.2f}%"
    except (TypeError, ValueError):
        return "N/A"


def _safe_float(val) -> float | None:
    try:
        if val is None or pd.isna(val):
            return None
        return float(val)
    except (TypeError, ValueError):
        return None


def _apply_year_window(df: pd.DataFrame, years: int) -> pd.DataFrame:
    """Apply a rolling year window. years<=0 keeps full history."""
    if years <= 0 or "fiscal_year" not in df.columns or df.empty:
        return df

    year_series = pd.to_numeric(df["fiscal_year"], errors="coerce")
    max_year = year_series.max()
    if pd.isna(max_year):
        return df
    cutoff = int(max_year) - years + 1
    return df[year_series >= cutoff]


def _extract_sql_tables(sql: str) -> set[str]:
    tables = set()
    patterns = [
        r"\bfrom\s+([a-zA-Z_][a-zA-Z0-9_]*)",
        r"\bjoin\s+([a-zA-Z_][a-zA-Z0-9_]*)",
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, sql, flags=re.IGNORECASE):
            tables.add(match.group(1).lower())
    return tables


def _format_records(df: pd.DataFrame, max_rows: int = 80) -> str:
    if df.empty:
        return "No rows returned."

    trimmed = df.head(max_rows).copy()
    for col in trimmed.columns:
        if pd.api.types.is_datetime64_any_dtype(trimmed[col]):
            trimmed[col] = trimmed[col].astype(str)
    return trimmed.to_string(index=False)


def _format_transcript_source(company: str, quarter, year, date_value) -> str:
    quarter_label = f"Q{quarter}" if quarter not in (None, "", "?") else "Q?"
    date_str = "unknown date"
    if date_value:
        date_str = str(date_value)[:10]
    return f"[Transcript: {company} {quarter_label} {year}, call date {date_str}]"


# ── Tool definitions ──────────────────────────────────────────────────────────


@tool
def get_financials(metric: str, company: str = "all", years: int = 5) -> str:
    """Get financial metrics from income statements or cash flows.

    Args:
        metric: The metric to retrieve. Common choices:
            Income: is_sales_revenue_turnover (revenue), is_gross_profit, is_oper_income,
                    is_net_income, ebitda, gross_margin, oper_margin, profit_margin
            Cash: cf_cash_from_oper, cf_free_cash_flow, cf_cap_expenditures, cf_dvd_paid
        company: Ticker or company name, or "all" for all companies.
        years: Number of years of history (default 5).
    """
    # Try each data source
    for loader in [load_income_statements, load_cash_flows]:
        df = loader()
        if metric in df.columns:
            break
    else:
        return f"Metric '{metric}' not found in financial statements."

    if df.empty:
        return "No financial data available."

    df = _apply_year_window(df, years)

    if company.lower() != "all":
        ticker = _resolve_ticker(company)
        if not ticker:
            return f"Company '{company}' not recognized."
        name = COMPANY_NAMES[ticker]
        df = df[df["company"] == name]

    if df.empty:
        return "No data found."

    df = df.sort_values(["company", "fiscal_year"], ascending=[True, False])
    lines = []
    for _, row in df.iterrows():
        val = _fmt_number(row.get(metric))
        lines.append(f"{row['company']} ({row['fiscal_year']}): {metric} = {val}")
    return "\n".join(lines)


@tool
def get_ratios(company: str = "all", years: int = 5) -> str:
    """Get profitability ratios: ROE, ROA, ROIC, margins, tax rate, payout ratio.

    Args:
        company: Ticker or company name, or "all" for all companies.
        years: Number of years of history.
    """
    df = load_ratios()
    if df.empty:
        return "No ratio data available."

    df = _apply_year_window(df, years)

    if company.lower() != "all":
        ticker = _resolve_ticker(company)
        if not ticker:
            return f"Company '{company}' not recognized."
        df = df[df["company"] == COMPANY_NAMES[ticker]]

    df = df.sort_values(["company", "fiscal_year"], ascending=[True, False])

    key_cols = ["company", "fiscal_year", "return_on_inv_capital", "return_com_eqy",
                "return_on_asset", "gross_margin", "oper_margin", "profit_margin"]
    available = [c for c in key_cols if c in df.columns]
    subset = df[available]

    lines = []
    for _, row in subset.iterrows():
        parts = [f"{row['company']} ({row['fiscal_year']}):"]
        for col in available[2:]:
            label = col.replace("_", " ").title()
            parts.append(f"  {label}: {_safe_pct(row.get(col))}")
        lines.append("\n".join(parts))
    return "\n\n".join(lines)


@tool
def search_transcripts(query: str, company: str = "all", years: int = 0, max_results: int = 20) -> str:
    """Search earnings call transcripts for keywords. Use for questions about
    strategy, AI, innovation, sustainability, M&A, market outlook, etc.

    Returns matched excerpts with explicit transcript source labels so the agent
    can cite transcript evidence in its final answer.

    Args:
        query: Keywords to search for in transcript text.
    """
    transcripts = load_all_transcripts()
    if not transcripts:
        return "No transcript data available."

    query_lower = (query or "").lower()
    query_terms = re.findall(r"[a-z0-9]+", query_lower)
    requested_ticker = _resolve_ticker(company) if company.lower() != "all" else None
    if requested_ticker is None and company.lower() == "all":
        # Infer company from natural-language prompt, e.g., "Michelin's 2025 transcript".
        for ticker, cname in COMPANY_NAMES.items():
            name_terms = re.findall(r"[a-z0-9]+", cname.lower())
            if ticker.lower() in query_lower or any(term in query_terms for term in name_terms):
                requested_ticker = ticker
                break

    requested_years = {
        int(m.group(0))
        for m in re.finditer(r"\b(19\d{2}|20\d{2})\b", query_lower)
    }
    stop_terms = {
        "transcript", "transcripts", "earning", "earnings", "call", "calls",
        "summarize", "summary", "michelin", "goodyear", "bridgestone",
        "continental", "pirelli", "sumitomo", "q", "quarter",
    }
    content_terms = [t for t in query_terms if not t.isdigit() and t not in stop_terms]
    current_year = pd.Timestamp.utcnow().year
    cutoff_year = current_year - years + 1 if years > 0 else None
    results = []

    for ticker, transcript_list in transcripts.items():
        if requested_ticker and ticker != requested_ticker:
            continue
        company = COMPANY_NAMES.get(ticker, ticker)
        for t_data in transcript_list:
            content = t_data.get("content", "")
            if not content:
                continue

            year = int(t_data.get("year") or 0)
            if cutoff_year and year and year < cutoff_year:
                continue
            if requested_years and year and year not in requested_years:
                continue

            # Find paragraphs containing the query terms
            paragraphs = content.split("\n\n")
            matches = []
            for para in paragraphs:
                if any(term in para.lower() for term in content_terms):
                    matches.append(para.strip()[:500])

            # Metadata fallback: if user asked for a specific period, return opening
            # excerpts even when keyword-in-body matching is sparse.
            if not matches and requested_years:
                for para in paragraphs:
                    clean = para.strip()
                    if clean:
                        matches.append(clean[:500])
                    if len(matches) >= 2:
                        break

            if matches:
                quarter = t_data.get("quarter", "?")
                source = _format_transcript_source(company, quarter, year, t_data.get("date"))
                excerpt_blocks = []
                for match in matches[:3]:
                    excerpt_blocks.append(f"Source: {source}\nQuote: {match}")
                header = f"## {company} (Q{quarter} {year} Earnings Call)"
                results.append(header + "\n" + "\n---\n".join(excerpt_blocks))
                if len(results) >= max_results:
                    return "\n\n".join(results)

    if not results:
        # Build a helpful coverage note so the agent can give an informed answer.
        coverage = {}
        for ticker, transcript_list in transcripts.items():
            if requested_ticker and ticker != requested_ticker:
                continue
            years_available = sorted({int(t["year"]) for t in transcript_list if t.get("year")})
            if years_available:
                coverage[COMPANY_NAMES.get(ticker, ticker)] = years_available

        if coverage:
            lines = [f"No mentions of '{query}' found in available earnings call transcripts."]
            lines.append("Available transcript years by company:")
            for company, years in coverage.items():
                lines.append(f"  {company}: {min(years)}–{max(years)} ({len(years)} transcripts)")
            return "\n".join(lines)

        return f"No earnings call transcripts are available. No mentions of '{query}' found."
    return "\n\n".join(results)


@tool
def search_news(query: str, company: str = "all", years: int = 0, max_results: int = 20) -> str:
    """Search recent news articles for all tire companies.

    Args:
        query: Keywords to search for in news headlines and text.
    """
    all_news = load_all_news()
    query_terms = [t for t in query.lower().split() if t]
    requested_ticker = _resolve_ticker(company) if company.lower() != "all" else None
    current_year = pd.Timestamp.utcnow().year
    cutoff_year = current_year - years + 1 if years > 0 else None
    results = []

    for ticker, articles in all_news.items():
        if requested_ticker and ticker != requested_ticker:
            continue
        company = COMPANY_NAMES.get(ticker, ticker)
        for article in articles:
            title = article.get("title", "")
            text = article.get("article_text", "")
            date = article.get("published_date", "")[:10]
            if cutoff_year and isinstance(date, str) and len(date) >= 4 and date[:4].isdigit():
                if int(date[:4]) < cutoff_year:
                    continue

            if any(term in title.lower() or term in text.lower() for term in query_terms):
                snippet = text[:300] + "..." if len(text) > 300 else text
                results.append(f"[{company}] {date} — {title}\n{snippet}")

            if len(results) >= max_results:
                return "\n\n".join(results)

    if not results:
        return f"No news articles found matching '{query}'."
    return "\n\n".join(results)


@tool
def get_stock_performance(company: str = "all", period_days: int = 252) -> str:
    """Get stock price performance over a given period.

    Args:
        company: Ticker or name, or "all".
        period_days: Number of trading days to look back (252 = 1 year, 63 = 1 quarter).
    """
    df = load_stock_prices()
    if df.empty:
        return "No stock price data available."

    results = []
    companies = [company] if company.lower() != "all" else list(COMPANY_NAMES.values())

    for comp in companies:
        if company.lower() != "all":
            ticker = _resolve_ticker(comp)
            if not ticker:
                return f"Company '{comp}' not recognized."
            comp = COMPANY_NAMES[ticker]

        cdf = df[df["company"] == comp].sort_values("date", ascending=False)
        if len(cdf) < 2:
            continue

        cdf = cdf.head(period_days)
        latest = cdf.iloc[0]
        earliest = cdf.iloc[-1]

        price_now = _safe_float(latest["adj_close"])
        price_then = _safe_float(earliest["adj_close"])
        if price_now is None or price_then is None:
            continue
        if price_then > 0:
            change_pct = ((price_now - price_then) / price_then) * 100
        else:
            change_pct = 0

        results.append(
            f"{comp}: ${price_now:.2f} (as of {str(latest['date'])[:10]})\n"
            f"  {period_days}-day change: {change_pct:+.1f}%  "
            f"(from ${price_then:.2f} on {str(earliest['date'])[:10]})"
        )

    return "\n\n".join(results) if results else "No data found."


@tool
def get_company_overview(company: str) -> str:
    """Get a company profile with key financial highlights.

    Args:
        company: Ticker or company name.
    """
    ticker = _resolve_ticker(company)
    if not ticker:
        return f"Company '{company}' not recognized."

    profiles = load_profiles()
    profile = profiles.get(ticker, {})

    name = profile.get("company_name", COMPANY_NAMES.get(ticker, ticker))
    parts = [f"# {name} ({ticker})"]

    for field in ["description", "sector", "industry", "ceo",
                  "full_time_employees", "country", "website"]:
        val = profile.get(field)
        if val:
            parts.append(f"**{field.replace('_', ' ').title()}**: {val}")

    # Add latest financials
    inc = load_income_statements()
    if not inc.empty:
        latest = inc[inc["company"] == COMPANY_NAMES[ticker]].sort_values(
            "fiscal_year", ascending=False
        )
        if not latest.empty:
            row = latest.iloc[0]
            parts.append(f"\n**Latest Financials ({row['fiscal_year']}):**")
            parts.append(f"  Revenue: {_fmt_number(row.get('is_sales_revenue_turnover'))}")
            parts.append(f"  Net Income: {_fmt_number(row.get('is_net_income'))}")
            parts.append(f"  EBITDA: {_fmt_number(row.get('ebitda'))}")

    return "\n".join(parts)


@tool
def get_data_coverage() -> str:
    """Return row counts and date/year coverage for core financial and text datasets."""
    if not DUCKDB_PATH.exists():
        return (
            "DuckDB database not found at data/processed/curated/financial_analyst.duckdb. "
            "Run data/load/process_to_duckdb.py first."
        )

    conn = duckdb.connect(str(DUCKDB_PATH), read_only=True)
    try:
        checks = {
            "income_statements": "SELECT COUNT(*) AS rows, MIN(fiscal_year) AS min_year, MAX(fiscal_year) AS max_year FROM income_statements",
            "cash_flows": "SELECT COUNT(*) AS rows, MIN(fiscal_year) AS min_year, MAX(fiscal_year) AS max_year FROM cash_flows",
            "ratios": "SELECT COUNT(*) AS rows, MIN(fiscal_year) AS min_year, MAX(fiscal_year) AS max_year FROM ratios",
            "stock_prices": "SELECT COUNT(*) AS rows, MIN(date) AS min_date, MAX(date) AS max_date FROM stock_prices",
            "news_articles": "SELECT COUNT(*) AS rows, MIN(published_date) AS min_date, MAX(published_date) AS max_date FROM news_articles",
            "transcripts": "SELECT COUNT(*) AS rows, MIN(year) AS min_year, MAX(year) AS max_year FROM transcripts",
        }

        lines = []
        for name, sql in checks.items():
            row = conn.execute(sql).fetchdf().iloc[0].to_dict()
            lines.append(f"{name}: {row}")
        return "\n".join(lines)
    finally:
        conn.close()


@tool
def query_financial_database(sql_query: str) -> str:
    """Query the local DuckDB analytics store for advanced analysis.

    Rules:
    - Only SELECT/CTE queries are allowed.
    - Allowed tables: companies, profiles, income_statements, cash_flows, ratios,
      stock_prices, news_articles, transcripts, news_summaries,
      transcript_summaries, transcript_company_summaries.
    - Results are capped to 200 rows.
    """
    query = (sql_query or "").strip().rstrip(";")
    if not query:
        return "Empty SQL query."

    lowered = query.lower()
    if not (lowered.startswith("select") or lowered.startswith("with")):
        return "Only SELECT or WITH queries are allowed."

    blocked_keywords = [
        "insert", "update", "delete", "drop", "alter", "create", "replace",
        "truncate", "attach", "detach", "copy", "pragma", "call", "vacuum",
    ]
    if any(re.search(rf"\b{k}\b", lowered) for k in blocked_keywords):
        return "Query contains blocked SQL keywords."

    referenced_tables = _extract_sql_tables(lowered)
    unknown_tables = [t for t in referenced_tables if t not in ALLOWED_TABLES]
    if unknown_tables:
        return f"Unknown or disallowed table(s): {', '.join(sorted(unknown_tables))}"

    if not DUCKDB_PATH.exists():
        return "DuckDB database not found at data/processed/curated/financial_analyst.duckdb."

    wrapped = f"SELECT * FROM ({query}) AS q LIMIT {MAX_SQL_ROWS}"
    conn = duckdb.connect(str(DUCKDB_PATH), read_only=True)
    try:
        df = conn.execute(wrapped).fetchdf()
        lines = [f"Returned {len(df)} rows (capped at {MAX_SQL_ROWS})."]
        lines.append(_format_records(df))
        return "\n".join(lines)
    except Exception as exc:
        return f"SQL error: {exc}"
    finally:
        conn.close()


@tool
def search_patent_filings(
    query: str,
    company: str = "all",
    years: int = 0,
    max_results: int = 20,
    ai_only: bool = False,
) -> str:
    """Search summarized patent filings for technology themes and innovation signals.

    Args:
        query: Keywords to search across invention title, AI type, category, and summary.
        company: Ticker/company name, or "all".
        years: Rolling filing-year window. 0 means full history.
        max_results: Maximum formatted hits returned.
        ai_only: If true, keep only patents classified as AI-driven.
    """
    df = load_ai_patent_summaries()
    if df.empty:
        return "No patent summary data available. Run data/transform/summarize_uspto_patents_with_ollama.py first."

    work = df.copy()
    work["filing_date"] = pd.to_datetime(work.get("filing_date"), errors="coerce")

    if company.lower() != "all":
        ticker = _resolve_ticker(company)
        if not ticker:
            return f"Company '{company}' not recognized."
        company_name = COMPANY_NAMES.get(ticker, ticker)
        work = work[(work.get("ticker") == ticker) | (work.get("company") == company_name)]

    if years > 0:
        cutoff_year = pd.Timestamp.utcnow().year - years + 1
        work = work[work["filing_date"].dt.year >= cutoff_year]

    if ai_only and "ai_driven" in work.columns:
        work = work[work["ai_driven"] == True]

    if query.strip():
        terms = [t.strip().lower() for t in query.split() if t.strip()]
        search_blob = (
            work.get("invention_title", "").fillna("").astype(str)
            + " "
            + work.get("short_summary", "").fillna("").astype(str)
            + " "
            + work.get("patent_category", "").fillna("").astype(str)
            + " "
            + work.get("ai_type", "").fillna("").astype(str)
        ).str.lower()
        mask = pd.Series(True, index=work.index)
        for term in terms:
            mask = mask & search_blob.str.contains(term, regex=False)
        work = work[mask]

    if work.empty:
        return f"No patent filings found matching '{query}'."

    if "confidence" in work.columns:
        work["confidence"] = pd.to_numeric(work["confidence"], errors="coerce").fillna(0.0)
    else:
        work["confidence"] = 0.0

    work = work.sort_values(["filing_date", "confidence"], ascending=[False, False])
    rows = work.head(max_results)

    lines = [f"Returned {len(rows)} patent filing summaries (of {len(work)} matches)."]
    for _, row in rows.iterrows():
        company_name = row.get("company") or COMPANY_NAMES.get(str(row.get("ticker", "")), str(row.get("ticker", "")))
        filing_date = "unknown date"
        if pd.notna(row.get("filing_date")):
            filing_date = str(row.get("filing_date"))[:10]
        app_num = str(row.get("application_number", "")).strip() or "unknown application"
        title = str(row.get("invention_title", "")).strip() or "Untitled invention"
        category = str(row.get("patent_category", "other")).strip() or "other"
        ai_type = str(row.get("ai_type", "none")).strip() or "none"
        confidence = float(row.get("confidence", 0.0) or 0.0)
        summary = str(row.get("short_summary", "")).strip()
        lines.append(
            f"Source: [Patent: {company_name}, app {app_num}, filed {filing_date}]\n"
            f"Title: {title}\n"
            f"Category: {category}; AI Type: {ai_type}; Confidence: {confidence:.2f}\n"
            f"Summary: {summary}"
        )

    return "\n\n".join(lines)


ALL_TOOLS = [
    get_financials,
    get_ratios,
    search_transcripts,
    search_patent_filings,
    search_news,
    get_stock_performance,
    get_company_overview,
    get_data_coverage,
    query_financial_database,
]

TOOL_REGISTRY = {tool.name: tool for tool in ALL_TOOLS}
