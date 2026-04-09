"""Load pre-downloaded JSON data into pandas DataFrames, with USD conversion."""

import json
from functools import lru_cache
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"

TICKERS = ["MGDDY", "GT", "BRDCY", "CTTAY", "PLLIF", "SSUMY"]

COMPANY_NAMES = {
    "MGDDY": "Michelin",
    "GT": "Goodyear",
    "BRDCY": "Bridgestone",
    "CTTAY": "Continental",
    "PLLIF": "Pirelli",
    "SSUMY": "Sumitomo",
}

BRAND_COLORS = {
    "Michelin": "#FCE300",
    "Goodyear": "#0033A0",
    "Bridgestone": "#E60012",
    "Continental": "#FFA500",
    "Pirelli": "#D4AF37",
    "Sumitomo": "#006241",
}

# ── Annual average exchange rates to USD ──────────────────────────────────────
# Sources: Federal Reserve / ECB average annual rates
_EUR_USD = {
    "2010": 1.33, "2011": 1.39, "2012": 1.29, "2013": 1.33, "2014": 1.33,
    "2015": 1.11, "2016": 1.11, "2017": 1.13, "2018": 1.18, "2019": 1.12,
    "2020": 1.14, "2021": 1.18, "2022": 1.05, "2023": 1.08, "2024": 1.08,
    "2025": 1.06,
}
_JPY_USD = {
    "2010": 0.0114, "2011": 0.0125, "2012": 0.0125, "2013": 0.0103,
    "2014": 0.0094, "2015": 0.0083, "2016": 0.0092, "2017": 0.0089,
    "2018": 0.0091, "2019": 0.0092, "2020": 0.0094, "2021": 0.0091,
    "2022": 0.0076, "2023": 0.0071, "2024": 0.0065, "2025": 0.0066,
}

# Columns that represent monetary values (not ratios/percentages/counts)
_MONETARY_PREFIXES = (
    "is_",
    "ebitda",
    "ebita",
    "ebit",
    "cf_",
    "net_debt",
    "free_cash_flow_equity",
)
_NON_MONETARY = {"cash_flow_to_net_inc"}
_RATIO_COLS = {"gross_margin", "oper_margin", "profit_margin", "ebitda_margin"}


def _is_monetary_col(col: str) -> bool:
    """Check if a column holds monetary values that need currency conversion."""
    if col in _NON_MONETARY or col in _RATIO_COLS:
        return False
    return any(col.startswith(p) for p in _MONETARY_PREFIXES)


def _get_fx_rate(currency: str, fiscal_year: str) -> float:
    """Get the USD conversion rate for a given currency and year."""
    if currency == "USD":
        return 1.0
    fy = str(fiscal_year)
    if currency == "EUR":
        return _EUR_USD.get(fy, 1.08)  # fallback to recent
    if currency == "JPY":
        return _JPY_USD.get(fy, 0.0066)
    return 1.0  # unknown currency, no conversion


def _convert_to_usd(df: pd.DataFrame) -> pd.DataFrame:
    """Convert monetary columns to USD based on currency and fiscal_year."""
    if df.empty or "currency" not in df.columns or "fiscal_year" not in df.columns:
        return df

    df = df.copy()
    monetary_cols = [c for c in df.columns if _is_monetary_col(c)]
    if not monetary_cols:
        return df

    # Compute FX rate per row
    df["_fx_rate"] = df.apply(
        lambda row: _get_fx_rate(row.get("currency", "USD"), row.get("fiscal_year", "")),
        axis=1,
    )

    for col in monetary_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce") * df["_fx_rate"]

    df["currency"] = "USD"
    df.drop(columns=["_fx_rate"], inplace=True)
    return df


# ── File loaders ──────────────────────────────────────────────────────────────

def _load_json(subfolder: str, ticker: str) -> list | dict | None:
    path = DATA_DIR / subfolder / f"{ticker}.json"
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _load_all_as_df(subfolder: str, convert_usd: bool = True) -> pd.DataFrame:
    frames = []
    for ticker in TICKERS:
        data = _load_json(subfolder, ticker)
        if data and isinstance(data, list) and len(data) > 0:
            df = pd.DataFrame(data)
            df["company"] = COMPANY_NAMES.get(ticker, ticker)
            frames.append(df)
    if not frames:
        return pd.DataFrame()
    result = pd.concat(frames, ignore_index=True)
    if convert_usd:
        result = _convert_to_usd(result)
    return result


@lru_cache(maxsize=1)
def load_income_statements() -> pd.DataFrame:
    return _load_all_as_df("income_statements")


@lru_cache(maxsize=1)
def load_cash_flows() -> pd.DataFrame:
    return _load_all_as_df("cash_flows")


@lru_cache(maxsize=1)
def load_ratios() -> pd.DataFrame:
    # Ratios are percentages, no currency conversion needed
    return _load_all_as_df("ratios", convert_usd=False)


@lru_cache(maxsize=1)
def load_stock_prices() -> pd.DataFrame:
    frames = []
    for ticker in TICKERS:
        data = _load_json("stock_prices", ticker)
        if data and isinstance(data, list):
            df = pd.DataFrame(data)
            df["ticker"] = ticker
            df["company"] = COMPANY_NAMES.get(ticker, ticker)
            frames.append(df)
    if not frames:
        return pd.DataFrame()
    result = pd.concat(frames, ignore_index=True)
    result["date"] = pd.to_datetime(result["date"])
    return result.sort_values(["company", "date"])


@lru_cache(maxsize=1)
def load_profiles() -> dict:
    profiles = {}
    for ticker in TICKERS:
        data = _load_json("profiles", ticker)
        if data and isinstance(data, list) and len(data) > 0:
            profiles[ticker] = data[0]
    return profiles


@lru_cache(maxsize=None)
def load_news(ticker: str) -> list:
    data = _load_json("news", ticker)
    return data if isinstance(data, list) else []


@lru_cache(maxsize=None)
def load_transcripts(ticker: str) -> list:
    """Load all transcripts for a ticker (list of dicts with year, quarter, content)."""
    data = _load_json("transcripts", ticker)
    if isinstance(data, list):
        return data
    # Handle old format: single dict
    if isinstance(data, dict) and data.get("content"):
        return [data]
    return []


@lru_cache(maxsize=1)
def load_all_transcripts() -> dict:
    """Load all transcripts for all tickers. Returns {ticker: [transcript_dicts]}."""
    transcripts = {}
    for ticker in TICKERS:
        t = load_transcripts(ticker)
        if t:
            transcripts[ticker] = t
    return transcripts


@lru_cache(maxsize=1)
def load_all_news() -> dict:
    all_news = {}
    for ticker in TICKERS:
        all_news[ticker] = load_news(ticker)
    return all_news
