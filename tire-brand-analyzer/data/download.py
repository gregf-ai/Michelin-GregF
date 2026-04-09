"""
One-time script to download financial data from roic.ai API.
Run locally: python data/download.py
Data is saved as JSON and committed to the repo for offline use.
"""

import json
import os
import time
from datetime import datetime, timezone
import requests

API_KEY = os.environ.get("ROIC_API_KEY", "")
BASE_URL = "https://api.roic.ai"

TICKERS = ["MGDDY", "GT", "BRDCY", "CTTAY", "PLLIF", "SSUMY"]

# Each entry: (subfolder, url_template, extra_params)
ENDPOINTS = [
    ("profiles",          "/v2/company/profile/{ticker}",              {}),
    ("income_statements", "/v2/fundamental/income-statement/{ticker}", {"period": "annual", "limit": 15}),
    ("cash_flows",        "/v2/fundamental/cash-flow/{ticker}",        {"period": "annual", "limit": 15}),
    ("stock_prices",      "/v2/stock-prices/{ticker}",                 {"limit": 2520}),
    ("ratios",            "/v2/fundamental/ratios/profitability/{ticker}",{"period": "annual", "limit": 15}),
]

# News/transcripts lookback window
LOOKBACK_YEARS = 10

# News pagination controls
NEWS_PAGE_SIZE = 50
NEWS_MAX_PAGES = 100

DATA_DIR = os.path.join(os.path.dirname(__file__), "raw")


def _fetch_json(session, url, params):
    """Fetch JSON from API with error handling."""
    resp = session.get(url, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def _save_json(filepath, data):
    """Save data as JSON."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _extract_news_year(article):
    """Extract article year from known date fields if available."""
    if not isinstance(article, dict):
        return None

    for key in ("published_date", "publishedDate", "date", "published_at", "publishedAt"):
        value = article.get(key)
        if isinstance(value, str) and len(value) >= 4 and value[:4].isdigit():
            return int(value[:4])
    return None


def download_standard_endpoints(session, ticker):
    """Download standard single-request endpoints."""
    for subfolder, url_template, params in ENDPOINTS:
        url = BASE_URL + url_template.format(ticker=ticker)
        query = {"apikey": API_KEY, **params}
        filepath = os.path.join(DATA_DIR, subfolder, f"{ticker}.json")

        print(f"  {subfolder:20s} -> ", end="", flush=True)
        try:
            data = _fetch_json(session, url, query)
            _save_json(filepath, data)
            count = len(data) if isinstance(data, list) else 1
            print(f"OK ({count} records)")
        except requests.exceptions.HTTPError as e:
            print(f"HTTP ERROR: {e}")
        except Exception as e:
            print(f"ERROR: {e}")
        time.sleep(0.3)


def download_news(session, ticker):
    """Download up to LOOKBACK_YEARS of news with pagination."""
    print(f"  {'news':20s} -> ", end="", flush=True)
    all_articles = []
    current_year = datetime.now(timezone.utc).year
    cutoff_year = current_year - (LOOKBACK_YEARS - 1)

    try:
        for page in range(NEWS_MAX_PAGES):
            url = BASE_URL + f"/v2/company/news/{ticker}"
            query = {"apikey": API_KEY, "limit": NEWS_PAGE_SIZE, "page": page}
            data = _fetch_json(session, url, query)
            if not isinstance(data, list) or len(data) == 0:
                break

            oldest_year_in_page = None
            for article in data:
                year = _extract_news_year(article)
                if year is not None:
                    oldest_year_in_page = year if oldest_year_in_page is None else min(oldest_year_in_page, year)

                # Keep undated records, plus records in the lookback window.
                if year is None or year >= cutoff_year:
                    all_articles.append(article)

            # Pages are returned newest-first; once we cross the cutoff year, stop.
            if oldest_year_in_page is not None and oldest_year_in_page < cutoff_year:
                break

            time.sleep(0.3)

        filepath = os.path.join(DATA_DIR, "news", f"{ticker}.json")
        _save_json(filepath, all_articles)
        print(f"OK ({len(all_articles)} articles)")
    except Exception as e:
        print(f"ERROR: {e}")


def download_transcripts(session, ticker):
    """Download all available transcripts (up to LOOKBACK_YEARS)."""
    print(f"  {'transcripts':20s} -> ", end="", flush=True)
    try:
        # First get the list of available transcripts
        url = BASE_URL + f"/v2/company/earnings-calls/list/{ticker}"
        listing = _fetch_json(session, url, {"apikey": API_KEY})

        if not isinstance(listing, list) or len(listing) == 0:
            print("no transcripts available")
            # Save empty list so loader doesn't break
            filepath = os.path.join(DATA_DIR, "transcripts", f"{ticker}.json")
            _save_json(filepath, [])
            return

        current_year = datetime.now(timezone.utc).year
        cutoff_year = current_year - (LOOKBACK_YEARS - 1)

        # Filter to configured lookback window (inclusive)
        recent = [t for t in listing if t.get("year", 0) >= cutoff_year]
        if not recent:
            recent = listing[:4]  # fallback: take the 4 most recent

        all_transcripts = []
        for entry in recent:
            year = entry.get("year")
            quarter = entry.get("quarter")
            if not year or not quarter:
                continue

            url = BASE_URL + f"/v2/company/earnings-calls/transcript/{ticker}"
            query = {"apikey": API_KEY, "year": year, "quarter": quarter}
            try:
                transcript = _fetch_json(session, url, query)
                if isinstance(transcript, dict) and transcript.get("content"):
                    all_transcripts.append(transcript)
                time.sleep(0.3)
            except Exception:
                pass  # skip individual failures

        filepath = os.path.join(DATA_DIR, "transcripts", f"{ticker}.json")
        _save_json(filepath, all_transcripts)
        print(f"OK ({len(all_transcripts)} transcripts)")
    except requests.exceptions.HTTPError:
        print("not available")
        filepath = os.path.join(DATA_DIR, "transcripts", f"{ticker}.json")
        _save_json(filepath, [])
    except Exception as e:
        print(f"ERROR: {e}")


def download_all():
    session = requests.Session()
    os.makedirs(DATA_DIR, exist_ok=True)

    for ticker in TICKERS:
        print(f"\n{'='*50}")
        print(f"Downloading data for {ticker}")
        print(f"{'='*50}")

        download_standard_endpoints(session, ticker)
        download_news(session, ticker)
        download_transcripts(session, ticker)

    print(f"\nDone! Data saved to {DATA_DIR}")


if __name__ == "__main__":
    download_all()
