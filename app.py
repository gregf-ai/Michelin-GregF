import base64
import os
import traceback
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import AIMessage, HumanMessage

from src.data_loader import COMPANY_NAMES
from src.graph import build_graph

st.set_page_config(
    page_title="Wheel Street",
    page_icon="●",
    layout="wide",
    initial_sidebar_state="expanded",
)

ARTICLE_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Libre+Baskerville:wght@400;700&family=IBM+Plex+Sans:wght@400;500;600&display=swap');

:root {
    --ink: #111111;
    --muted: #6f6f6f;
    --line: #d9d9d9;
    --soft: #f3f3f3;
    --card: #fafafa;
    --paper: #ffffff;
}

.stApp {
    background: linear-gradient(180deg, #ffffff 0%, #f6f6f6 100%);
}

/* Keep header visible so Streamlit's native sidebar reopen control remains available */
[data-testid="stHeader"] {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
}

/* Keep Streamlit's native sidebar controls available (collapse + reopen). */
[data-testid="stSidebarCollapseButton"],
[data-testid="stSidebarCollapsedControl"] {
    display: flex !important;
}

[data-testid="block-container"] {
    max-width: 1560px;
    padding-top: 0.85rem;
    padding-bottom: 4rem;
}

body, .stMarkdown, .stCaption, .stText, .stTabs, .stMetric {
    font-family: 'IBM Plex Sans', sans-serif;
    font-size: 1.15rem;
    color: var(--ink);
}

h1, h2, h3, h4 {
    font-family: 'Libre Baskerville', serif;
    color: var(--ink);
    letter-spacing: -0.02em;
}

.article-shell {
    background: rgba(255,255,255,0.88);
    border: 1px solid rgba(17,17,17,0.08);
    box-shadow: 0 18px 50px rgba(17,17,17,0.06);
    padding: 0 2.5rem 2.75rem;
}

.eyebrow {
    font-size: 1.2rem;
    font-weight: 600;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: var(--muted);
    margin-bottom: 0.9rem;
}

.hero-title {
    font-size: clamp(3.2rem, 4.5vw, 5.5rem);
    line-height: 1.05;
    margin: 0 0 1rem 0;
    max-width: 14ch;
}

.hero-deck {
    max-width: 60ch;
    font-size: 1.4rem;
    line-height: 1.8;
    color: #303030;
    margin-bottom: 1.75rem;
}

.section-title {
    margin-top: 1rem;
    margin-bottom: 0.65rem;
    font-size: 2.4rem;
}

.section-deck {
    max-width: 58ch;
    font-size: 1.25rem;
    line-height: 1.75;
    color: #3d3d3d;
    margin-bottom: 1.5rem;
}

.kicker-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 0.9rem;
    margin: 1.4rem 0 2rem 0;
}

.kicker-card {
    border-top: 2px solid var(--ink);
    background: var(--soft);
    padding: 0.85rem 0.95rem 0.95rem;
}

.kicker-label {
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 0.12em;
    font-size: 0.95rem;
}

.kicker-value {
    font-family: 'Libre Baskerville', serif;
    font-size: 2.1rem;
    margin-top: 0.45rem;
}

/* ── Chat panel: dark card container ── */
.chat-panel [data-testid="stVerticalBlockBorderWrapper"] {
    background: linear-gradient(180deg, #161616 0%, #121212 100%);
    border: 1px solid #2f2f2f;
    border-radius: 18px;
    box-shadow: 0 20px 44px rgba(0,0,0,0.22);
    padding: 0.95rem 0.95rem 0.8rem;
}

/* Inner scroll area (the st.container with height) */
.chat-panel [data-testid="stVerticalBlockBorderWrapper"]
    [data-testid="stVerticalBlockBorderWrapper"] {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 14px;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.04);
}

/* Text colours inside chat panel */
.chat-panel, .chat-panel p, .chat-panel span,
.chat-panel [data-testid="stMarkdownContainer"] {
    color: #f0f0f0 !important;
}

.chat-panel [data-testid="stMarkdownContainer"],
.chat-panel [data-testid="stChatMessage"] p,
.chat-panel [data-testid="stChatMessage"] li,
.chat-panel [data-testid="stChatMessage"] div {
    font-size: 0.82rem !important;
    line-height: 1.38 !important;
}

.chat-panel .stCaption,
.chat-panel [data-testid="stCaptionContainer"] {
    font-size: 0.76rem !important;
    line-height: 1.35 !important;
}

.chat-panel [data-testid="stChatMessage"] {
    background: rgba(255, 255, 255, 0.02);
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 10px;
    padding: 0.35rem 0.45rem;
    margin-bottom: 0.3rem;
}

/* Compact chat avatars/icons */
.chat-panel [data-testid="stChatMessageAvatarUser"],
.chat-panel [data-testid="stChatMessageAvatarAssistant"] {
    width: 1.35rem !important;
    height: 1.35rem !important;
    min-width: 1.35rem !important;
    min-height: 1.35rem !important;
}

.chat-panel [data-testid="stChatMessageAvatarUser"] *,
.chat-panel [data-testid="stChatMessageAvatarAssistant"] * {
    font-size: 0.68rem !important;
}

/* Chat input field and placeholder on dark background */
.chat-panel [data-testid="stChatInput"] textarea,
.chat-panel [data-testid="stChatInput"] input {
    color: #f4f4f4 !important;
    background: #191919 !important;
    border: 1px solid #3a3a3a !important;
    font-size: 0.8rem !important;
}

.chat-panel [data-testid="stChatInput"] textarea::placeholder,
.chat-panel [data-testid="stChatInput"] input::placeholder {
    color: #a6a6a6 !important;
}

/* Starter prompt button contrast */
.chat-panel [data-testid="stButton"] button,
.chat-panel [data-testid="stButton"] button[kind="secondary"] {
    background: #2a2a2a !important;
    border: 1px solid #474747 !important;
    color: #f0f0f0 !important;
    -webkit-text-fill-color: #f0f0f0 !important;
    opacity: 1 !important;
}

section[data-testid="stSidebar"] [class*="st-key-clear_chat_button"] button,
section[data-testid="stSidebar"] [class*="st-key-toggle_prompts_button"] button {
    background-color: #242424 !important;
    background-image: none !important;
    border: 1px solid #5a5a5a !important;
    color: #f0f0f0 !important;
    -webkit-text-fill-color: #f0f0f0 !important;
    opacity: 1 !important;
    font-size: 0.82rem !important;
    font-weight: 600 !important;
    line-height: 1.28 !important;
}

section[data-testid="stSidebar"] [class*="st-key-clear_chat_button"] button *,
section[data-testid="stSidebar"] [class*="st-key-toggle_prompts_button"] button * {
    color: #f0f0f0 !important;
    -webkit-text-fill-color: #f0f0f0 !important;
    font-size: 0.82rem !important;
    line-height: 1.28 !important;
}

section[data-testid="stSidebar"] [class*="st-key-clear_chat_button"] button:hover,
section[data-testid="stSidebar"] [class*="st-key-toggle_prompts_button"] button:hover {
    background-color: #323232 !important;
    background-image: none !important;
    border-color: #8a8a8a !important;
    color: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
}

section[data-testid="stSidebar"] [class*="st-key-clear_chat_button"] button:hover *,
section[data-testid="stSidebar"] [class*="st-key-toggle_prompts_button"] button:hover * {
    color: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
}

.chat-panel [data-testid="stButton"] button *,
.chat-panel [data-testid="stButton"] button span,
.chat-panel [data-testid="stButton"] button p {
    color: #f0f0f0 !important;
    -webkit-text-fill-color: #f0f0f0 !important;
}

.chat-panel [data-testid="stButton"] button:hover,
.chat-panel [data-testid="stButton"] button[kind="secondary"]:hover {
    background: #ffffff !important;
    border-color: #ffffff !important;
    color: #111111 !important;
    -webkit-text-fill-color: #111111 !important;
}

.chat-panel [data-testid="stButton"] button:hover *,
.chat-panel [data-testid="stButton"] button:hover span,
.chat-panel [data-testid="stButton"] button:hover p {
    color: #111111 !important;
    -webkit-text-fill-color: #111111 !important;
}

/* Force styling specifically for starter prompt buttons in sidebar */
section[data-testid="stSidebar"] [class*="st-key-single_page_suggestion_"] button {
    background-color: #2a2a2a !important;
    background-image: none !important;
    border: 1px solid #474747 !important;
    color: #f0f0f0 !important;
    -webkit-text-fill-color: #f0f0f0 !important;
    opacity: 1 !important;
    font-size: 0.82rem !important;
    line-height: 1.28 !important;
}

section[data-testid="stSidebar"] [class*="st-key-single_page_suggestion_"] button * {
    color: #f0f0f0 !important;
    -webkit-text-fill-color: #f0f0f0 !important;
    font-size: 0.82rem !important;
    line-height: 1.28 !important;
}

section[data-testid="stSidebar"] [class*="st-key-single_page_suggestion_"] button:hover {
    background-color: #ffffff !important;
    background-image: none !important;
    border-color: #ffffff !important;
    color: #111111 !important;
    -webkit-text-fill-color: #111111 !important;
}

section[data-testid="stSidebar"] [class*="st-key-single_page_suggestion_"] button:hover * {
    color: #111111 !important;
    -webkit-text-fill-color: #111111 !important;
}

/* Thin dark scrollbar */
.chat-panel ::-webkit-scrollbar { width: 4px; }
.chat-panel ::-webkit-scrollbar-track { background: #1e1e1e; }
.chat-panel ::-webkit-scrollbar-thumb { background: #444; border-radius: 2px; }

.sticky-chat {
    position: sticky;
    top: 1.2rem;
}

.tbd-card {
    border-left: 3px solid var(--ink);
    padding: 1rem 1rem 1rem 1.15rem;
    background: var(--soft);
    color: #333333;
    line-height: 1.8;
}

.chart-note {
    color: var(--muted);
    font-size: 1.05rem;
    margin-bottom: 0.6rem;
}

.overview-list {
    display: flex;
    flex-direction: column;
    gap: 0.7rem;
}

.overview-panel {
    border-left: 3px solid var(--ink);
    background: #f5f5f5;
    padding: 1rem 1.1rem 1rem 1.15rem;
}

.overview-head {
    font-weight: 700;
    font-size: 1.2rem;
    margin-bottom: 0.35rem;
}

.overview-subhead {
    color: #4a4a4a;
    margin-bottom: 0.85rem;
}

.overview-rank-label {
    color: #2b2b2b;
    font-size: 0.95rem;
    font-weight: 600;
    margin: -0.35rem 0 0.35rem;
}

.overview-line {
    display: grid;
    grid-template-columns: 5.4rem 1fr;
    gap: 0.85rem;
    align-items: start;
    padding: 0.45rem 0;
}

.overview-left {
    font-weight: 700;
    color: #111111;
    white-space: nowrap;
}

.overview-main {
    font-size: 1.06rem;
    line-height: 1.55;
    color: #666666;
    word-break: break-word;
}

.overview-main strong {
    color: #111111;
}

.overview-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.8rem;
    padding: 0.72rem 0.85rem;
    background: #f4f4f4;
    border: 1px solid #e4e4e4;
}

.overview-label {
    font-weight: 600;
    font-size: 1.15rem;
    letter-spacing: 0.01em;
}

.overview-right {
    display: inline-flex;
    align-items: center;
    gap: 0.6rem;
    font-weight: 600;
}

.status-circle {
    width: 1.8rem;
    height: 1.8rem;
    border-radius: 50%;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 1.1rem;
    line-height: 1;
    font-weight: 700;
}

.status-top1 {
    background: #1b5e20;
    color: #ffffff;
}

.status-top3 {
    background: #93c47d;
    color: transparent;
}

.status-other {
    background: #b22222;
    color: #ffffff;
}

div[data-baseweb="tab-list"] {
    gap: 0.4rem;
}

button[data-baseweb="tab"] {
    background: #f2f2f2;
    border-radius: 0;
    border: 1px solid #dddddd;
    padding: 0.75rem 1.2rem;
    font-size: 1.05rem;
}

button[data-baseweb="tab"][aria-selected="true"] {
    background: #111111;
    color: #ffffff;
    border-color: #111111;
}

.hero-banner {
    position: relative;
    width: calc(100% + 5rem);
    min-height: 375px;
    background-size: cover;
    background-position: center 35%;
    margin: -0.85rem -2.5rem 2rem -2.5rem;
    overflow: hidden;
}

.hero-overlay {
    position: absolute;
    inset: 0;
    background: linear-gradient(120deg, rgba(0,0,0,0.82) 0%, rgba(0,0,0,0.48) 55%, rgba(0,0,0,0.18) 100%);
    z-index: 0;
}

.hero-content {
    position: relative;
    z-index: 1;
    padding: 3.5rem 2.5rem 2.75rem;
}

.hero-content .eyebrow { color: rgba(255,255,255,0.62); }
.hero-content .hero-title { color: #ffffff; }
.hero-content .hero-deck { color: rgba(255,255,255,0.82); }

@media (max-width: 900px) {
    .article-shell {
        padding: 1.4rem 1rem 2rem;
    }

    .kicker-grid {
        grid-template-columns: 1fr;
    }

    .sticky-chat {
        position: static;
    }

    .hero-banner {
        width: calc(100% + 2rem);
        margin-left: -1rem;
        margin-right: -1rem;
    }

}

/* Tab container: subtle border to separate from chat and patents */
[data-testid="stTabs"] {
    background: linear-gradient(180deg, rgba(248,248,248,0.5) 0%, rgba(250,250,250,0.5) 100%);
    border: 1px solid rgba(17,17,17,0.06);
    border-radius: 8px;
    padding: 1rem;
    margin-bottom: 1rem;
}

/* ── Streamlit default sidebar (dark themed) ── */
/* Keep default row order so sidebar stays on the left. */
[data-testid="stAppViewContainer"] {
    flex-direction: row;
}

section[data-testid="stSidebar"] {
    background: #0f0f0f !important;
    border: none !important;
    box-shadow: none !important;
}

section[data-testid="stSidebar"] > div {
    padding-top: 0.4rem;
}

/* Sidebar label / header */
section[data-testid="stSidebar"]::before {
    content: "Analyst";
    display: block;
    font-family: 'IBM Plex Sans', sans-serif;
    font-size: 0.78rem;
    font-weight: 600;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    color: #ffffff;
    padding: 0.9rem 1.2rem 0.4rem;
}

/* Title & text inside sidebar */
section[data-testid="stSidebar"] h4,
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] span,
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] {
    color: #f0f0f0 !important;
}

section[data-testid="stSidebar"] [data-testid="stChatMessage"] {
    background: transparent;
}
</style>
"""

GRAYSCALE = ["#111111", "#555555", "#8c8c8c", "#b4b4b4", "#d0d0d0", "#e5e5e5"]
PATENT_LINE_COLORS = ["#111111", "#3f5f4a", "#8a4f4f", "#3d4f78", "#7a623e", "#4e4e4e"]
PEER_ORDER = [COMPANY_NAMES[t] for t in COMPANY_NAMES]
CURATED_DIR = Path(__file__).resolve().parent / "data" / "processed" / "curated"
ENV_FILE_PATH = Path(__file__).resolve().parent / ".env"
HERO_IMG_PATH = Path(__file__).resolve().parent / "static" / "bull.jpg"


def get_hero_bg_css() -> str:
    if HERO_IMG_PATH.exists():
        b64 = base64.b64encode(HERO_IMG_PATH.read_bytes()).decode()
        return (
            "<style>"
            ".hero-banner {"
            f"background-image: linear-gradient(120deg, rgba(0,0,0,0.82) 0%, rgba(0,0,0,0.48) 55%, rgba(0,0,0,0.18) 100%), url('data:image/jpeg;base64,{b64}');"
            "}"
            "</style>"
        )
    return ""


def format_pct(value: float | None) -> str:
    if value is None or pd.isna(value):
        return "N/A"
    return f"{value:.1f}%"


def get_latest_metric_year(df: pd.DataFrame, metric: str) -> int | None:
    scoped = df.dropna(subset=[metric, "fiscal_year"]).copy()
    if scoped.empty:
        return None
    return int(scoped["fiscal_year"].max())


@st.cache_data
def prepare_competitive_frames() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, int]:
    income = pd.read_csv(CURATED_DIR / "income_statements_usd.csv")
    stock_prices = pd.read_csv(CURATED_DIR / "stock_prices.csv")
    cash_flows = pd.read_csv(CURATED_DIR / "cash_flows_usd.csv")
    ratios = pd.read_csv(CURATED_DIR / "ratios.csv")

    income["fiscal_year"] = pd.to_numeric(income["fiscal_year"], errors="coerce")
    income = income.dropna(subset=["fiscal_year"]).sort_values(["company", "fiscal_year"])
    margin = income.dropna(subset=["fiscal_year", "ebitda_margin"]).sort_values(["company", "fiscal_year"])

    income["revenue_growth"] = income.groupby("company")["is_sales_revenue_turnover"].pct_change() * 100
    income["ebitda_growth"] = income.groupby("company")["ebitda"].pct_change() * 100

    # Use split-adjusted close so annual growth is robust to stock splits.
    stock_prices["date"] = pd.to_datetime(stock_prices["date"], errors="coerce")
    stock_prices = stock_prices.dropna(subset=["date", "adj_close", "company"]).sort_values(["company", "date"])
    stock_prices["fiscal_year"] = stock_prices["date"].dt.year
    year_end_prices = stock_prices.groupby(["company", "fiscal_year"], as_index=False).tail(1)
    year_end_prices = year_end_prices.sort_values(["company", "fiscal_year"])
    year_end_prices["annual_stock_growth"] = year_end_prices.groupby("company")["adj_close"].pct_change() * 100

    cash_flows["fiscal_year"] = pd.to_numeric(cash_flows["fiscal_year"], errors="coerce")
    cash_flows = cash_flows.dropna(subset=["fiscal_year", "cf_dvd_paid", "company"]).sort_values(["company", "fiscal_year"])
    # Dividends paid are commonly negative cash outflows, so use absolute values for intuitive growth.
    cash_flows["dividend_paid_abs"] = cash_flows["cf_dvd_paid"].abs()
    cash_flows["dividend_growth"] = cash_flows.groupby("company")["dividend_paid_abs"].pct_change() * 100
    # Remove known outlier that distorts peer comparison.
    cash_flows.loc[
        (cash_flows["fiscal_year"] == 2012)
        & (cash_flows["company"].astype(str).str.contains("Continental", case=False, na=False)),
        "dividend_growth",
    ] = pd.NA

    ratios["fiscal_year"] = pd.to_numeric(ratios["fiscal_year"], errors="coerce")
    ratios = ratios.dropna(subset=["fiscal_year", "return_on_inv_capital", "company"]).sort_values(["company", "fiscal_year"])

    latest_year = int(margin["fiscal_year"].max()) if not margin.empty else 0
    return income, margin, year_end_prices, cash_flows, ratios, stock_prices, latest_year


@st.cache_data
def prepare_patent_frames() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build yearly patent count frames for all companies."""
    from src.data_loader import load_patent_filings, load_ai_patent_summaries

    filings = load_patent_filings()
    if not filings.empty:
        yearly_raw = (
            filings.dropna(subset=["filing_year"])
            .groupby(["company", "filing_year"], as_index=False)
            .size()
            .rename(columns={"size": "patent_count"})
        )
        yearly_raw["fiscal_year"] = yearly_raw["filing_year"].astype(int)
        yearly_raw = yearly_raw.drop(columns=["filing_year"])
    else:
        yearly_raw = pd.DataFrame(columns=["company", "fiscal_year", "patent_count"])

    ai_df = load_ai_patent_summaries()
    if not ai_df.empty:
        ai_driven = ai_df[ai_df["ai_driven"] == True]  # noqa: E712
        if not ai_driven.empty:
            ai_yearly_raw = (
                ai_driven.dropna(subset=["filing_year"])
                .groupby(["company", "filing_year"], as_index=False)
                .size()
                .rename(columns={"size": "ai_patent_count"})
            )
            ai_yearly_raw["fiscal_year"] = ai_yearly_raw["filing_year"].astype(int)
            ai_yearly_raw = ai_yearly_raw.drop(columns=["filing_year"])
        else:
            ai_yearly_raw = pd.DataFrame(columns=["company", "fiscal_year", "ai_patent_count"])
    else:
        ai_yearly_raw = pd.DataFrame(columns=["company", "fiscal_year", "ai_patent_count"])

    return yearly_raw, ai_yearly_raw


def latest_metric_frame(df: pd.DataFrame, metric: str) -> pd.DataFrame:
    year = get_latest_metric_year(df, metric)
    if year is None:
        return pd.DataFrame(columns=df.columns)

    latest = df[(df["fiscal_year"] == year) & (~df[metric].isna())].copy()
    latest["company"] = pd.Categorical(latest["company"], categories=PEER_ORDER, ordered=True)
    return latest.sort_values(metric, ascending=False)


def year_metric_frame(df: pd.DataFrame, metric: str, year: int) -> pd.DataFrame:
    scoped = df[(df["fiscal_year"] == year) & (~df[metric].isna())].copy()
    if scoped.empty:
        return pd.DataFrame(columns=df.columns)
    scoped["company"] = pd.Categorical(scoped["company"], categories=PEER_ORDER, ordered=True)
    return scoped.sort_values(metric, ascending=False)


def comparison_metric_frame(df: pd.DataFrame, metric: str, basis: str) -> tuple[pd.DataFrame, str]:
    if basis == "2025":
        year_frame = year_metric_frame(df, metric, 2025)
        if not year_frame.empty:
            return year_frame, "Comparison basis: 2025 values."
        fallback = latest_metric_frame(df, metric)
        if fallback.empty:
            return fallback, "Comparison basis unavailable."
        fallback_year = get_latest_metric_year(df, metric)
        return fallback, f"2025 values unavailable; showing latest available year ({fallback_year})."

    return median_metric_frame(df, metric), "Comparison basis: 10-year median values."


def get_company_rank(df: pd.DataFrame, metric: str, company: str = "Michelin") -> int | None:
    ranked = median_metric_frame(df, metric).reset_index(drop=True)
    rows = ranked.index[ranked["company"] == company]
    if len(rows) == 0:
        return None
    return int(rows[0]) + 1


def rank_emoji(rank: int | None) -> str:
    sq = "<span style='display:inline-block;width:1em;height:1em;border-radius:2px;vertical-align:middle;margin-right:2px;background:{color}'></span>"
    if rank is None:
        return sq.format(color="#aaaaaa")
    if rank == 1:
        return sq.format(color="#1a5c35")
    if rank == 2:
        return sq.format(color="#2ecc71")
    if rank <= 4:
        return sq.format(color="#f1c40f")
    return sq.format(color="#e74c3c")

def render_overview_rankings(
    ratios_data: pd.DataFrame,
    margin_data: pd.DataFrame,
    income: pd.DataFrame,
    stock_growth_data: pd.DataFrame,
    dividend_growth_data: pd.DataFrame,
    patent_yearly: pd.DataFrame,
    ai_patent_yearly: pd.DataFrame,
) -> None:
    def _item(label: str, description: str, df: pd.DataFrame, metric: str) -> dict[str, object]:
        ranked = median_metric_frame(df, metric).reset_index(drop=True)
        rows = ranked.index[ranked["company"] == "Michelin"]
        rank = int(rows[0]) + 1 if len(rows) else None
        leader = str(ranked.iloc[0]["company"]) if not ranked.empty else None
        return {
            "label": label,
            "description": description,
            "rank": rank,
            "leader": leader,
        }

    # Keep these overview bullets explicitly hard-coded and in a fixed display order.
    items: list[dict[str, object]] = [
        _item(
            "ROIC",
            "Return on invested capital, capturing how efficiently operating capital is converted into returns.",
            ratios_data,
            "return_on_inv_capital",
        ),
        _item(
            "Margin",
            "EBITDA margin, a read on operating profitability and pricing discipline.",
            margin_data,
            "ebitda_margin",
        ),
        _item(
            "Revenue Growth",
            "Year-over-year top-line growth to gauge demand momentum and market capture.",
            income,
            "revenue_growth",
        ),
        _item(
            "EBITDA Growth",
            "Year-over-year EBITDA growth as a signal of earnings power expansion.",
            income,
            "ebitda_growth",
        ),
        _item(
            "Annual Stock Growth",
            "Year-over-year change in split-adjusted year-end stock price as a market verdict.",
            stock_growth_data,
            "annual_stock_growth",
        ),
        _item(
            "Dividend Growth",
            "Growth in dividends paid, indicating payout durability and cash distribution strength.",
            dividend_growth_data,
            "dividend_growth",
        ),
        _item(
            "Patent Applications per Year",
            "Annual USPTO patent applications, a proxy for innovation pipeline and R&D output.",
            patent_yearly,
            "patent_count",
        ),
        _item(
            "AI Patent Applications per Year",
            "Annual AI-driven patent applications (LLM-classified), indicating AI R&D intensity.",
            ai_patent_yearly,
            "ai_patent_count",
        ),
    ]

    items.sort(key=lambda x: x["rank"] if x["rank"] is not None else 999)

    lines: list[str] = []
    for item in items:
        rank = item["rank"]
        rank_text = f"#{rank}" if rank is not None else "N/A"
        emoji = rank_emoji(rank)
        leader_note = ""
        if rank is None:
            leader_note = " Data unavailable for Michelin in this metric."
        elif rank != 1 and item["leader"]:
            leader_note = f" <strong style='color:#111111'>Leader:</strong> <span style='color:#111111'>{item['leader']}</span>."

        lines.append(
            "<div class='overview-line'>"
            f"<div class='overview-left'>{emoji} {rank_text}</div>"
            f"<div class='overview-main'><strong>{item['label']}</strong>: {item['description']}{leader_note}</div>"
            "</div>"
        )

    st.markdown(
        "<div class='overview-panel'>"
        "<div class='overview-head'>Michelin Competitive Scorecard</div>"
        "<div class='overview-subhead'>Sorted by Michelin rank (lowest to highest). Rank is Michelin's position among 5 peers on 10-year median.</div>"
        "<div class='overview-rank-label'>Rank</div>"
        + "".join(lines)
        + "</div>",
        unsafe_allow_html=True,
    )


def median_metric_frame(df: pd.DataFrame, metric: str) -> pd.DataFrame:
    median = (
        df.dropna(subset=[metric])
        .groupby("company", as_index=False)[metric]
        .median()
    )
    median["company"] = pd.Categorical(median["company"], categories=PEER_ORDER, ordered=True)
    return median.sort_values(metric, ascending=False)


def build_rank_bar(ranked: pd.DataFrame, metric: str) -> go.Figure:
    companies = ranked["company"].tolist()
    tick_text = [f"<b>{c}</b>" if c == "Michelin" else c for c in companies]
    has_neg = bool((ranked[metric] < 0).any())

    def _bar(subset: pd.DataFrame, outside: bool) -> go.Bar:
        return go.Bar(
            x=subset[metric],
            y=subset["company"],
            orientation="h",
            marker=dict(color="#111111", line=dict(color="#111111", width=0)),
            selected=dict(marker=dict(color="#aaaaaa")),
            unselected=dict(marker=dict(color="#111111")),
            customdata=subset[["company"]],
            text=[format_pct(v) for v in subset[metric]],
            textposition="outside" if outside else "inside",
            insidetextanchor="start" if not outside else None,
            textfont=dict(size=15, color="#111111" if outside else "#ffffff"),
            cliponaxis=False,
            hovertemplate="%{y}: %{x:.1f}%<extra></extra>",
            showlegend=False,
        )

    if has_neg:
        traces = []
        pos_rows = ranked[ranked[metric] >= 0]
        neg_rows = ranked[ranked[metric] < 0]
        if not pos_rows.empty:
            traces.append(_bar(pos_rows, outside=True))
        if not neg_rows.empty:
            traces.append(_bar(neg_rows, outside=False))
        fig = go.Figure(data=traces)
    else:
        fig = go.Figure(_bar(ranked, outside=True))

    fig.update_layout(
        height=420,
        margin=dict(l=0, r=70, t=8, b=8),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        barmode="overlay",
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False, title="", fixedrange=True),
        yaxis=dict(
            showgrid=False, zeroline=False, showticklabels=True, title="",
            tickmode="array",
            tickvals=companies,
            ticktext=tick_text,
            tickfont=dict(size=17, color="#111111"),
            autorange="reversed",
            fixedrange=True,
        ),
        dragmode=False,
    )
    return fig


def build_top3_trend(df: pd.DataFrame, metric: str, top3: list[str] | None = None) -> go.Figure:
    if top3 is None:
        ranked = latest_metric_frame(df, metric)
        top3 = ranked.head(3)[["company"]]["company"].tolist()
    trend = df[df["company"].isin(top3)].dropna(subset=[metric]).copy()

    fig = go.Figure()
    for idx, company in enumerate(top3):
        cdf = trend[trend["company"] == company].sort_values("fiscal_year")
        if cdf.empty:
            continue
        fig.add_trace(
            go.Scatter(
                x=cdf["fiscal_year"],
                y=cdf[metric],
                mode="lines+markers",
                name=company,
                line=dict(color=GRAYSCALE[idx], width=2.5),
                marker=dict(size=6, color=GRAYSCALE[idx]),
                hovertemplate=f"{company}<br>%{{x}}: %{{y:.1f}}%<extra></extra>",
            )
        )

    fig.update_layout(
        height=420,
        margin=dict(l=8, r=12, t=8, b=8),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(x=1.01, y=0.5, xanchor="left", yanchor="middle", bgcolor="rgba(0,0,0,0)", borderwidth=0, font=dict(size=16)),
        xaxis=dict(showgrid=False, title="", tickfont=dict(size=15, color="#666666")),
        yaxis=dict(showgrid=True, gridcolor="#ececec", zeroline=False, showticklabels=False, title=""),
    )
    return fig


def build_sparkline_stack(df: pd.DataFrame, metric: str, companies: list[str]) -> go.Figure:
    n = len(companies)
    fig = make_subplots(rows=n, cols=1, shared_xaxes=True, vertical_spacing=0.15)
    yaxis_refs = ["y"] + [f"y{i + 1}" for i in range(1, n)]
    
    # Determine if this is a growth metric (center at 0) or margin/ROIC metric (center at median)
    is_growth_metric = metric in ["revenue_growth", "ebitda_growth", "annual_stock_growth", "dividend_growth"]

    for i, company in enumerate(companies):
        row = i + 1
        cdf = df[df["company"] == company].dropna(subset=[metric]).sort_values("fiscal_year")
        if cdf.empty:
            continue
        x_vals = cdf["fiscal_year"].tolist()
        y_vals = cdf[metric].tolist()
        
        if is_growth_metric:
            center_val = 0.0
            shading_color_above = "rgba(147,196,125,0.2)"  # green
            shading_color_below = "rgba(210,120,120,0.2)"  # red
            center_label = "0%"
        else:
            center_val = float(cdf[metric].median())
            shading_color_above = "rgba(160,160,160,0.2)"  # gray
            shading_color_below = "rgba(160,160,160,0.2)"  # gray
            center_label = format_pct(center_val)
        
        # Use tighter padding so lines occupy more of the available vertical space.
        value_range = max(y_vals) - min(y_vals)
        y_spread = max(value_range * 0.55, abs(max(y_vals) - center_val), abs(min(y_vals) - center_val), 0.25) * 1.06

        # Add area shading between data and center line
        fig.add_trace(go.Scatter(
            x=x_vals + x_vals[::-1],
            y=[max(v, center_val) for v in y_vals] + [center_val] * len(y_vals),
            mode="lines",
            fill="toself",
            fillcolor=shading_color_above,
            line=dict(width=0, color="rgba(0,0,0,0)"),
            showlegend=False,
            hoverinfo="skip",
        ), row=row, col=1)

        fig.add_trace(go.Scatter(
            x=x_vals + x_vals[::-1],
            y=[min(v, center_val) for v in y_vals] + [center_val] * len(y_vals),
            mode="lines",
            fill="toself",
            fillcolor=shading_color_below,
            line=dict(width=0, color="rgba(0,0,0,0)"),
            showlegend=False,
            hoverinfo="skip",
        ), row=row, col=1)

        # Center reference line
        fig.add_trace(go.Scatter(
            x=x_vals, y=[center_val] * len(x_vals),
            mode="lines", line=dict(color="#999999", width=1, dash="dot"),
            showlegend=False, hoverinfo="skip",
        ), row=row, col=1)

        # Data line with markers
        fig.add_trace(go.Scatter(
            x=x_vals, y=y_vals,
            mode="lines+markers",
            line=dict(color="#111111", width=2.5),
            marker=dict(size=5, color="#111111"),
            showlegend=False,
            hovertemplate=f"{company}: %{{y:.1f}}%<extra></extra>",
        ), row=row, col=1)
        
        # Find indices for min, max, first, last points
        min_idx = y_vals.index(min(y_vals))
        max_idx = y_vals.index(max(y_vals))
        first_idx = 0
        last_idx = len(y_vals) - 1
        label_indices = set([first_idx, last_idx, min_idx, max_idx])
        
        # Add value annotations ONLY for min, max, first, last
        for idx in label_indices:
            x, y = x_vals[idx], y_vals[idx]
            fig.add_annotation(
                xref=f"x{row if row > 1 else ''}", yref=yaxis_refs[i],
                x=x, y=y,
                text=f"{y:.0f}%",
                showarrow=False, yshift=8 if y >= center_val else -10,
                font=dict(size=11, color="#666666"),
            )

        # Company name and median annotation on right
        val_str = format_pct(float(cdf[metric].median()))
        fig.add_annotation(
            xref="paper", yref=yaxis_refs[i],
            x=1.02, y=y_vals[-1],
            text=f"<b>{company}</b><br>Median: {val_str}",
            showarrow=False, xanchor="left", yanchor="middle",
            font=dict(size=14, color="#111111"),
        )
        
        # Label with leader line for center value on left
        if is_growth_metric:
            # For 0 line, show subtle label and leader line
            fig.add_annotation(
                xref="paper", yref=yaxis_refs[i],
                x=-0.19, y=center_val,
                ax=-30, ay=0,
                showarrow=True, arrowhead=2, arrowsize=0.8, arrowwidth=0.5, arrowcolor="#999999",
                text="0%",
                font=dict(size=11, color="#666666"),
                xanchor="right", yanchor="middle",
            )
        else:
            # For median, show label with leader line
            fig.add_annotation(
                xref="paper", yref=yaxis_refs[i],
                x=-0.19, y=center_val,
                ax=-30, ay=0,
                showarrow=True, arrowhead=2, arrowsize=0.8, arrowwidth=0.5, arrowcolor="#999999",
                text=f"median {center_label}",
                font=dict(size=11, color="#666666"),
                xanchor="right", yanchor="middle",
            )
        
        fig.update_yaxes(
            range=[center_val - y_spread, center_val + y_spread],
            showgrid=False, zeroline=False, showticklabels=False, fixedrange=True,
            row=row, col=1,
        )
        fig.update_xaxes(
            showgrid=False, zeroline=False, fixedrange=True,
            showticklabels=(row == n),
            tickfont=dict(size=13, color="#666666"),
            row=row, col=1,
        )

    fig.update_layout(
        height=500,
        margin=dict(l=50, r=160, t=8, b=8),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
    )
    return fig


def build_company_history_bar(df: pd.DataFrame, metric: str, company: str) -> go.Figure:
    history = df[df["company"] == company].dropna(subset=[metric]).sort_values("fiscal_year")
    fig = go.Figure(
        go.Bar(
            x=history["fiscal_year"],
            y=history[metric],
            marker=dict(color="#555555", line=dict(color="#111111", width=0)),
            text=[format_pct(v) for v in history[metric]],
            textposition="outside",
            cliponaxis=False,
            hovertemplate=f"{company}<br>%{{x}}: %{{y:.1f}}%<extra></extra>",
        )
    )
    fig.update_layout(
        height=420,
        margin=dict(l=8, r=12, t=44, b=8),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        xaxis=dict(showgrid=False, title="", tickfont=dict(size=15, color="#666666")),
        yaxis=dict(showgrid=True, gridcolor="#ececec", zeroline=False, showticklabels=False, title=""),
    )
    return fig


def build_count_rank_bar(ranked: pd.DataFrame, metric: str) -> go.Figure:
    """Horizontal bar chart for count-based metrics (patents, not percentages)."""
    companies = ranked["company"].tolist()
    tick_text = [f"<b>{c}</b>" if c == "Michelin" else c for c in companies]
    fig = go.Figure(
        go.Bar(
            x=ranked[metric],
            y=ranked["company"],
            orientation="h",
            marker=dict(color="#111111", line=dict(color="#111111", width=0)),
            selected=dict(marker=dict(color="#aaaaaa")),
            unselected=dict(marker=dict(color="#111111")),
            customdata=ranked[["company"]],
            text=[f"{int(v):,}" for v in ranked[metric]],
            textposition="outside",
            textfont=dict(size=15, color="#111111"),
            cliponaxis=False,
            hovertemplate="%{y}: %{x:,.0f}<extra></extra>",
            showlegend=False,
        )
    )
    fig.update_layout(
        height=420,
        margin=dict(l=0, r=70, t=8, b=8),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        barmode="overlay",
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False, title="", fixedrange=True),
        yaxis=dict(
            showgrid=False, zeroline=False, showticklabels=True, title="",
            tickmode="array",
            tickvals=companies,
            ticktext=tick_text,
            tickfont=dict(size=17, color="#111111"),
            autorange="reversed",
            fixedrange=True,
        ),
        dragmode=False,
    )
    return fig


def build_patent_trend(df: pd.DataFrame, metric: str, companies: list[str]) -> go.Figure:
    """Multi-line trend chart of annual patent counts for the given companies."""
    fig = go.Figure()
    for idx, company in enumerate(companies):
        cdf = df[df["company"] == company].dropna(subset=[metric]).sort_values("fiscal_year")
        if cdf.empty:
            continue
        color = PATENT_LINE_COLORS[idx % len(PATENT_LINE_COLORS)]
        fig.add_trace(go.Scatter(
            x=cdf["fiscal_year"], y=cdf[metric],
            mode="lines+markers",
            name=company,
            line=dict(color=color, width=3),
            marker=dict(size=8, color=color, line=dict(color="#ffffff", width=1.2)),
            hovertemplate=f"{company}<br>%{{x}}: %{{y:,.0f}}<extra></extra>",
        ))
    fig.update_layout(
        height=420,
        margin=dict(l=8, r=12, t=8, b=8),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(x=1.01, y=0.5, xanchor="left", yanchor="middle", bgcolor="rgba(0,0,0,0)", borderwidth=0, font=dict(size=16)),
        xaxis=dict(showgrid=False, title="", tickfont=dict(size=15, color="#666666")),
        yaxis=dict(showgrid=True, gridcolor="#ececec", zeroline=False, showticklabels=False, title=""),
    )
    return fig


def build_company_patent_history(df: pd.DataFrame, metric: str, company: str) -> go.Figure:
    """Bar chart of annual patent count for a single company."""
    history = df[df["company"] == company].dropna(subset=[metric]).sort_values("fiscal_year")
    fig = go.Figure(
        go.Bar(
            x=history["fiscal_year"].astype(str),
            y=history[metric],
            marker=dict(color="#555555", line=dict(color="#111111", width=0)),
            text=[f"{int(v):,}" for v in history[metric]],
            textposition="outside",
            textfont=dict(size=15, color="#111111"),
            cliponaxis=False,
            hovertemplate=f"{company}<br>%{{x}}: %{{y:,.0f}}<extra></extra>",
        )
    )
    fig.update_layout(
        height=420,
        margin=dict(l=8, r=12, t=18, b=8),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        xaxis=dict(showgrid=False, title="", tickfont=dict(size=15, color="#666666"), type="category"),
        yaxis=dict(showgrid=True, gridcolor="#ececec", zeroline=False, showticklabels=False, title=""),
    )
    return fig


def build_company_underlying_bar(df: pd.DataFrame, value_col: str, company: str, hover_name: str) -> go.Figure:
    history = df[df["company"] == company].dropna(subset=[value_col]).sort_values("fiscal_year")
    y_millions = history[value_col] / 1_000_000
    fig = go.Figure(
        go.Bar(
            x=history["fiscal_year"],
            y=y_millions,
            marker=dict(color="#555555", line=dict(color="#111111", width=0)),
            text=[f"${v:,.0f}M" for v in y_millions],
            textposition="outside",
            textfont=dict(size=16, color="#111111"),
            cliponaxis=False,
            hovertemplate=f"{company}<br>%{{x}}: $%{{y:,.1f}}M {hover_name}<extra></extra>",
        )
    )
    fig.update_layout(
        height=420,
        margin=dict(l=8, r=12, t=18, b=8),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        xaxis=dict(showgrid=False, title="", tickfont=dict(size=15, color="#666666")),
        yaxis=dict(showgrid=True, gridcolor="#ececec", zeroline=False, showticklabels=False, title=""),
    )
    return fig


def build_company_stock_candlestick(stock_df: pd.DataFrame, company: str) -> go.Figure:
    cdf = stock_df[stock_df["company"] == company].copy()
    cdf = cdf.dropna(subset=["date", "adj_close"]).sort_values("date")
    cdf["fiscal_year"] = cdf["date"].dt.year
    yearly = cdf.groupby("fiscal_year", as_index=False).agg(
        open=("adj_close", "first"),
        high=("adj_close", "max"),
        low=("adj_close", "min"),
        close=("adj_close", "last"),
    )
    fig = go.Figure(
        go.Candlestick(
            x=yearly["fiscal_year"],
            open=yearly["open"],
            high=yearly["high"],
            low=yearly["low"],
            close=yearly["close"],
            increasing_line_color="#6f8a75",
            decreasing_line_color="#9a6a6a",
            increasing_fillcolor="#9fb2a4",
            decreasing_fillcolor="#c7a0a0",
            showlegend=False,
        )
    )
    fig.update_layout(
        height=420,
        margin=dict(l=8, r=12, t=18, b=8),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=False, title="", tickfont=dict(size=15, color="#666666")),
        yaxis=dict(showgrid=True, gridcolor="#ececec", zeroline=False, showticklabels=False, title=""),
        xaxis_rangeslider_visible=False,
    )
    return fig


def extract_selected_company(selection: object) -> str | None:
    if not selection:
        return None

    points: list[object] = []
    if isinstance(selection, dict):
        points = selection.get("selection", {}).get("points", [])
    else:
        state = getattr(selection, "selection", None)
        points = getattr(state, "points", []) if state is not None else []

    if not points:
        return None

    point = points[0]
    if isinstance(point, dict):
        customdata = point.get("customdata")
        if isinstance(customdata, list) and customdata:
            return str(customdata[0])
        if isinstance(customdata, str):
            return customdata
        return point.get("y")

    customdata = getattr(point, "customdata", None)
    if isinstance(customdata, list) and customdata:
        return str(customdata[0])
    if isinstance(customdata, str):
        return customdata
    return getattr(point, "y", None)


def get_metric_analysis(df: pd.DataFrame, metric: str, metric_label: str) -> str:
    """Generate analysis text for a metric including Michelin's rank, values, and trend."""
    median_val = df.dropna(subset=[metric])[metric].median()
    val_2025 = df[df["fiscal_year"] == 2025][metric]
    val_2025 = val_2025.iloc[0] if not val_2025.empty else None
    ranked = median_metric_frame(df, metric).reset_index(drop=True)
    michelin_rows = ranked.index[ranked["company"] == "Michelin"]
    rank = int(michelin_rows[0]) + 1 if len(michelin_rows) else None
    leader = str(ranked.iloc[0]["company"]) if not ranked.empty else None
    leader_val = ranked.iloc[0][metric] if not ranked.empty else None
    michelin_history = df[df["company"] == "Michelin"].dropna(subset=[metric]).sort_values("fiscal_year")[metric].tolist()
    trend = "increasing" if len(michelin_history) > 1 and michelin_history[-1] > michelin_history[0] else "decreasing"

    rank_str = f"#{rank}" if rank else "N/A"
    leader_str = f"led by {leader}" if leader and leader != "Michelin" else ""
    median_str = f"{format_pct(median_val)}" if median_val is not None else "N/A"
    val_2025_str = f"{format_pct(val_2025)}" if val_2025 is not None else "N/A"
    leader_val_str = f"{format_pct(leader_val)}" if leader_val is not None else "N/A"
    leader_clause = f" Peers are {leader_str} at {leader_val_str}." if leader_str else ""

    return (
        f"Michelin ranks {rank_str} among peers on 10-year median {metric_label.lower()}: {median_str}. "
        f"In 2025, the value was {val_2025_str}, "
        f"with a {trend} trend over the period.{leader_clause}"
    )


def render_metric_tab(title: str, note: str, df: pd.DataFrame, metric: str) -> None:
    metric_description_map = {
        "return_on_inv_capital": "Return on invested capital captures how efficiently operating capital is converted into returns.",
        "ebitda_margin": "EBITDA margin reflects operating profitability and pricing discipline.",
        "revenue_growth": "Revenue growth indicates demand momentum and market capture.",
        "ebitda_growth": "EBITDA growth signals earnings power expansion.",
        "annual_stock_growth": "Stock price change represents the market's verdict on competitive positioning.",
        "dividend_growth": "Dividend growth indicates payout durability and shareholder returns.",
    }
    metric_desc = metric_description_map.get(metric, "")
    analysis = get_metric_analysis(df, metric, title)

    # Render title with tooltip
    st.markdown(
        f"<h4 style='display: flex; align-items: center; gap: 0.5rem;'>"
        f"{title}"
        f"<span title='{metric_desc}' style='cursor: help; font-size: 0.9rem; color: #999; font-weight: normal;'>ⓘ</span>"
        f"</h4>",
        unsafe_allow_html=True
    )
    st.markdown(analysis, unsafe_allow_html=True)

    toggle_key = f"basis_{title.lower().replace(' ', '_')}"
    basis = st.radio(
        "Ranking basis",
        options=["2025", "10-yr median"],
        index=1,
        horizontal=True,
        key=toggle_key,
        label_visibility="collapsed",
    )

    ranked, basis_note = comparison_metric_frame(df, metric, basis)
    missing = [c for c in PEER_ORDER if c not in set(ranked["company"]) ]

    year_note = basis_note
    if missing:
        year_note += " Missing in this basis: " + ", ".join(missing) + "."

    chart_left, chart_divider, chart_right = st.columns([1, 0.03, 1.32], gap="medium")
    with chart_left:
        # Bar chart title based on toggle
        basis_display = basis if basis == "2025" else "10-Year Median"
        st.markdown(f"**{title} — {basis_display}**", unsafe_allow_html=True)
        # Descriptor below title with wrapping
        st.markdown(f"<div class='chart-note'>{note} {year_note}</div>", unsafe_allow_html=True)
        selection = st.plotly_chart(
            build_rank_bar(ranked, metric),
            width="stretch",
            config={"displayModeBar": False, "scrollZoom": False},
            key=f"rank_{title.lower().replace(' ', '_')}_{basis.lower().replace('-', '_')}",
            on_select="rerun",
            selection_mode="points",
        )
    with chart_divider:
        st.markdown(
            "<div style='height: 470px; width: 1px; background: #111111; opacity: 0.18; margin: 0 auto;'></div>",
            unsafe_allow_html=True,
        )
    with chart_right:
        selected_company = extract_selected_company(selection)
        if selected_company:
            if metric == "annual_stock_growth":
                right_title = f"**{selected_company} stock price over time**"
                right_sub = "<div class='chart-note' style='margin-top:-0.35rem;'>Yearly candlestick chart (open, high, low, close).</div>"
            elif metric == "revenue_growth":
                right_title = f"**{selected_company} revenue over time**"
                right_sub = "<div class='chart-note' style='margin-top:-0.35rem;'>Underlying annual revenue values.</div>"
            elif metric == "ebitda_growth":
                right_title = f"**{selected_company} EBITDA over time**"
                right_sub = "<div class='chart-note' style='margin-top:-0.35rem;'>Underlying annual EBITDA values.</div>"
            elif metric == "dividend_growth":
                right_title = f"**{selected_company} dividends over time**"
                right_sub = "<div class='chart-note' style='margin-top:-0.35rem;'>Underlying annual dividend values.</div>"
            else:
                right_title = f"**{selected_company} {title.lower()} over time**"
                right_sub = f"<div class='chart-note' style='margin-top:-0.35rem;'>{selected_company} over time.</div>"
        else:
            right_title = f"**{title} over time**"
            center_note = "centered at 0%." if metric in ["revenue_growth", "ebitda_growth", "annual_stock_growth", "dividend_growth"] else "centered at median."
            right_sub = f"<div class='chart-note' style='margin-top:-0.35rem;'>Michelin versus top 2 competitors, {center_note}</div>"

        st.markdown(right_title, unsafe_allow_html=True)
        st.markdown(right_sub, unsafe_allow_html=True)

        if selected_company:
            if metric == "annual_stock_growth":
                st.plotly_chart(
                    build_company_stock_candlestick(stock_prices_daily, selected_company),
                    width="stretch",
                    config={"displayModeBar": False},
                )
            elif metric == "revenue_growth":
                st.plotly_chart(
                    build_company_underlying_bar(df, "is_sales_revenue_turnover", selected_company, "Revenue"),
                    width="stretch",
                    config={"displayModeBar": False},
                )
            elif metric == "ebitda_growth":
                st.plotly_chart(
                    build_company_underlying_bar(df, "ebitda", selected_company, "EBITDA"),
                    width="stretch",
                    config={"displayModeBar": False},
                )
            elif metric == "dividend_growth":
                st.plotly_chart(
                    build_company_underlying_bar(df, "dividend_paid_abs", selected_company, "Dividends"),
                    width="stretch",
                    config={"displayModeBar": False},
                )
            else:
                st.plotly_chart(
                    build_company_history_bar(df, metric, selected_company),
                    width="stretch",
                    config={"displayModeBar": False},
                )
        else:
            others = [c for c in ranked["company"].tolist() if c != "Michelin"][:2]
            sparkline_companies = ["Michelin"] + others
            st.plotly_chart(build_sparkline_stack(df, metric, sparkline_companies), width="stretch", config={"displayModeBar": False, "scrollZoom": False})


def render_patent_tab(
    yearly_df: pd.DataFrame,
    metric: str,
    title: str,
    note: str,
    tab_key: str,
) -> None:
    """Render a patent analytics tab following the same structure as financial metric tabs."""
    if yearly_df.empty:
        st.info("Patent filing data is not yet available.")
        return

    # 10-year window based on max year in dataset
    max_yr = int(yearly_df["fiscal_year"].max())
    min_yr = max_yr - 9
    df_10yr = yearly_df[yearly_df["fiscal_year"] >= min_yr].copy()

    ranked = median_metric_frame(df_10yr, metric)

    if ranked.empty:
        st.info("Insufficient data to rank companies.")
        return

    top2 = [c for c in ranked["company"].tolist() if c != "Michelin"][:2]
    spotlight = ["Michelin"] + top2

    michelin_median = ranked[ranked["company"] == "Michelin"][metric]
    michelin_median_val = int(michelin_median.iloc[0]) if not michelin_median.empty else None
    michelin_rows = ranked.reset_index(drop=True)
    michelin_idx = michelin_rows.index[michelin_rows["company"] == "Michelin"]
    rank = int(michelin_idx[0]) + 1 if len(michelin_idx) else None
    leader = str(ranked.iloc[0]["company"]) if not ranked.empty else None

    rank_str = f"#{rank}" if rank else "N/A"
    leader_note = f" Leader: {leader}." if leader and leader != "Michelin" else ""
    median_str = f"{michelin_median_val:,}" if michelin_median_val is not None else "N/A"

    st.markdown(f"#### {title}")
    st.markdown(
        f"Michelin ranks **{rank_str}** among peers by 10-year median annual {title.lower()}: "
        f"**{median_str}** filings/year.{leader_note}"
    )

    chart_left, chart_divider, chart_right = st.columns([1, 0.03, 1.32], gap="medium")
    with chart_left:
        st.markdown(f"**{title} — 10-Year Median**", unsafe_allow_html=True)
        st.markdown(f"<div class='chart-note'>{note} Basis: {min_yr}–{max_yr}.</div>", unsafe_allow_html=True)
        selection = st.plotly_chart(
            build_count_rank_bar(ranked, metric),
            width="stretch",
            config={"displayModeBar": False, "scrollZoom": False},
            key=f"rank_{tab_key}",
            on_select="rerun",
            selection_mode="points",
        )
    with chart_divider:
        st.markdown(
            "<div style='height: 470px; width: 1px; background: #111111; opacity: 0.18; margin: 0 auto;'></div>",
            unsafe_allow_html=True,
        )
    with chart_right:
        selected_company = extract_selected_company(selection)
        if selected_company:
            st.markdown(f"**{selected_company} — patent applications per year**", unsafe_allow_html=True)
            st.markdown(
                f"<div class='chart-note' style='margin-top:-0.35rem;'>Annual {title.lower()} for {selected_company}.</div>",
                unsafe_allow_html=True,
            )
            st.plotly_chart(
                build_company_patent_history(yearly_df, metric, selected_company),
                width="stretch",
                config={"displayModeBar": False},
            )
        else:
            st.markdown(f"**{title} per year — Michelin vs. top 2 peers**", unsafe_allow_html=True)
            st.markdown(
                "<div class='chart-note' style='margin-top:-0.35rem;'>Annual filing counts. Click a company bar on the left to drill in.</div>",
                unsafe_allow_html=True,
            )
            st.plotly_chart(
                build_patent_trend(yearly_df, metric, spotlight),
                width="stretch",
                config={"displayModeBar": False, "scrollZoom": False},
            )


def get_openai_key_from_env_file() -> str:
    if not ENV_FILE_PATH.exists():
        return ""
    try:
        for line in ENV_FILE_PATH.read_text(encoding="utf-8", errors="ignore").splitlines():
            if line.strip().startswith("OPENAI_API_KEY="):
                return line.split("=", 1)[1].strip()
    except OSError:
        return ""
    return ""


def _normalize_api_base_url(raw_url: str) -> str:
    cleaned = (raw_url or "").strip().rstrip("/")
    if not cleaned:
        return ""
    if cleaned.startswith("http://") or cleaned.startswith("https://"):
        return cleaned
    # Render blueprints may inject a bare service host like "wheel-street-api".
    # Convert that to a publicly resolvable domain for browser-facing requests.
    if "." not in cleaned and cleaned != "localhost":
        return f"https://{cleaned}.onrender.com"
    return f"https://{cleaned}"


def _append_chat_message(role: str, text: str, meta: dict | None = None) -> None:
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    st.session_state.chat_history.append((role, text, meta or {}))


def _iter_chat_history() -> list[tuple[str, str, dict]]:
    normalized: list[tuple[str, str, dict]] = []
    for item in st.session_state.get("chat_history", []):
        if isinstance(item, tuple) and len(item) >= 2:
            role = item[0]
            text = item[1]
            meta = item[2] if len(item) > 2 and isinstance(item[2], dict) else {}
            normalized.append((role, text, meta))
    return normalized


def _render_remote_evidence(meta: dict) -> None:
    citations = meta.get("citations") or []
    tool_trace = meta.get("tool_trace") or []
    model = meta.get("model")

    if not citations and not tool_trace and not model:
        return

    with st.expander("Evidence", expanded=False):
        if model:
            st.caption(f"Model: {model}")

        if citations:
            st.markdown("**Citations**")
            for citation in citations:
                st.markdown(f"- {citation}")

        if tool_trace:
            st.markdown("**Tool Trace**")
            for step in tool_trace[:8]:
                tool_name = step.get("tool", "tool")
                status = step.get("status", "unknown")
                st.markdown(f"- {tool_name} ({status})")


def _remote_qa(api_base_url: str, history: list[tuple[str, str, dict]]) -> tuple[str, dict]:
    payload_messages = [
        {"role": role, "content": text}
        for role, text, _meta in history
        if role in {"user", "assistant"} and text
    ]
    resp = requests.post(
        f"{api_base_url}/qa",
        json={"messages": payload_messages},
        timeout=240,
    )
    if not resp.ok:
        detail = ""
        try:
            body = resp.json()
            detail = str(body.get("detail", "")).strip()
        except ValueError:
            detail = (resp.text or "").strip()
        if detail:
            raise RuntimeError(f"API error {resp.status_code}: {detail}")
        raise RuntimeError(f"API error {resp.status_code}: {resp.reason}")
    body = resp.json()
    answer = body.get("answer", "")
    if not answer:
        raise RuntimeError("API returned an empty answer.")

    meta = {
        "citations": body.get("citations") or [],
        "tool_trace": body.get("tool_trace") or [],
        "model": body.get("model") or "",
    }
    return answer, meta


def init_agent() -> None:
    remote_base = _normalize_api_base_url(os.environ.get("ANALYST_API_BASE_URL", ""))
    if remote_base:
        st.session_state.agent_mode = "remote"
        st.session_state.analyst_api_base_url = remote_base
        if "chat_history" not in st.session_state:
            st.session_state.chat_history = []
        return

    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        try:
            api_key = st.secrets.get("OPENAI_API_KEY", "")
        except StreamlitSecretNotFoundError:
            api_key = ""
    if not api_key:
        api_key = get_openai_key_from_env_file()
    if not api_key:
        return
    os.environ["OPENAI_API_KEY"] = api_key
    st.session_state.agent_mode = "local"
    if "agent" not in st.session_state:
        model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
        st.session_state.agent = build_graph(model_name=model)
    # chat_history stores (role, text, meta) tuples for rendering and remote evidence panels.
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []


class StreamlitProgressCallback(BaseCallbackHandler):
    def __init__(self, status_box: Any):
        self.status_box = status_box
        self.events: list[str] = []
        self.tool_labels = {
            "get_financials": "Reading income statement and cash flow data",
            "get_ratios": "Reading profitability and return ratios",
            "search_transcripts": "Searching earnings call transcripts",
            "search_patent_filings": "Searching patent filing summaries",
            "search_news": "Searching company news archive",
            "get_stock_performance": "Reviewing stock performance history",
            "get_company_overview": "Loading company overview",
            "get_data_coverage": "Checking local data coverage",
            "query_financial_database": "Running DuckDB financial query",
        }

    def _push(self, msg: str) -> None:
        self.events.append(msg)
        recent = self.events[-8:]
        self.status_box.markdown("\n".join(f"- {line}" for line in recent))

    def on_chain_start(self, serialized: dict[str, Any], inputs: dict[str, Any], **kwargs: Any) -> None:
        self._push("Planning answer and selecting tools")

    def on_chat_model_start(self, serialized: dict[str, Any], messages: list[list[Any]], **kwargs: Any) -> None:
        self._push("Reasoning with model")

    def on_tool_start(self, serialized: dict[str, Any], input_str: str, **kwargs: Any) -> None:
        tool_name = serialized.get("name", "tool")
        label = self.tool_labels.get(tool_name, f"Running tool: {tool_name}")
        self._push(label)

    def on_tool_end(self, output: Any, **kwargs: Any) -> None:
        self._push("Tool completed")

    def on_tool_error(self, error: BaseException, **kwargs: Any) -> None:
        self._push(f"Tool error: {type(error).__name__}")

    def on_chain_end(self, outputs: dict[str, Any], **kwargs: Any) -> None:
        self._push("Workflow finished")


def _render_chatbot_impl() -> None:
    init_agent()

    if "chat_busy" not in st.session_state:
        st.session_state.chat_busy = False
    if "show_starter_prompts" not in st.session_state:
        st.session_state.show_starter_prompts = True

    # Outer wrapper styled via .chat-panel CSS selector
    wrapper = st.container()
    with wrapper:
        st.caption(
            "Ask questions about Michelin and competitors' income statements, earnings call transcripts, and patents."
        )

        is_remote = st.session_state.get("agent_mode") == "remote"
        if not is_remote and "agent" not in st.session_state:
            st.info("OpenAI credentials are not available — chat is offline.")
            return

        history = _iter_chat_history()
        pending_question = st.session_state.pop("pending_question", None) if "pending_question" in st.session_state else None

        controls_col1, controls_col2, _controls_spacer = st.columns([1, 1, 2], gap="small")
        with controls_col1:
            prompts_label = "Hide prompts" if st.session_state.show_starter_prompts else "Starter prompts"
            if st.button(prompts_label, key="toggle_prompts_button", width="stretch"):
                st.session_state.show_starter_prompts = not st.session_state.show_starter_prompts
                st.rerun()
        with controls_col2:
            if st.button("Clear chat", key="clear_chat_button", width="stretch"):
                st.session_state.chat_history = []
                st.session_state.chat_busy = False
                st.session_state.show_starter_prompts = True
                st.session_state.pop("pending_question", None)
                st.rerun()

        if st.session_state.show_starter_prompts and not st.session_state.chat_busy and pending_question is None:
            suggestions = [
                "What explains Michelin's revenue growth versus Goodyear and Bridgestone?",
                "Why does Michelin have higher margins than its peers?",
                "Why has Sumitomo's stock price grown so rapidly?",
                "Summarize Michelin's 2025 earnings transcript",
                "Summarize the AI-related patents Michelin has filed",
            ]
            st.caption("Starter prompts")
            prompt_cols = st.columns(1, gap="small")
            for idx, suggestion in enumerate(suggestions):
                with prompt_cols[0]:
                    if st.button(suggestion, key=f"single_page_suggestion_{idx}", width="stretch"):
                        st.session_state.pending_question = suggestion
                        st.session_state.show_starter_prompts = False
                        st.rerun()

        # Keep the input near the top of the panel so no scrolling is needed to ask the first question.
        user_input = pending_question or st.chat_input("Ask a question about Michelin and peers")

        has_history = bool(history)
        chat_box = st.container(height=560 if (has_history or st.session_state.chat_busy) else 220, border=True)
        with chat_box:
            for role, text, meta in history:
                with st.chat_message(role):
                    st.markdown(text)
                    if role == "assistant":
                        _render_remote_evidence(meta)

        if user_input:
            st.session_state.chat_busy = True
            _append_chat_message("user", user_input)

            with chat_box:
                with st.chat_message("user"):
                    st.markdown(user_input)

                with st.chat_message("assistant"):
                    try:
                        if is_remote:
                            api_base = st.session_state.get("analyst_api_base_url", "")
                            response_text, meta = _remote_qa(api_base, _iter_chat_history())
                            st.markdown(response_text)
                            _render_remote_evidence(meta)
                            _append_chat_message("assistant", response_text, meta)
                        else:
                            clean_messages = []
                            for role, text, _meta in _iter_chat_history()[:-1]:
                                if role == "user":
                                    clean_messages.append(HumanMessage(content=text))
                                else:
                                    clean_messages.append(AIMessage(content=text))
                            clean_messages.append(HumanMessage(content=user_input))

                            progress = st.status("LangChain progress", expanded=True)
                            callback = StreamlitProgressCallback(progress)
                            result = st.session_state.agent.invoke(
                                {"messages": clean_messages},
                                config={"callbacks": [callback]},
                            )
                            progress.update(label="LangChain complete", state="complete", expanded=False)

                            response = result["messages"][-1]
                            st.markdown(response.content)
                            _append_chat_message("assistant", response.content)
                    except Exception as exc:
                        tb = traceback.format_exc()
                        print(tb)
                        short = str(exc) or type(exc).__name__
                        error_msg = f"The analyst hit an error: {short}"
                        with st.expander("Error detail"):
                            st.code(tb)
                        st.error(error_msg)
                        _append_chat_message("assistant", error_msg)
                    finally:
                        st.session_state.chat_busy = False
            st.rerun()


if hasattr(st, "fragment"):
    render_chatbot = st.fragment(_render_chatbot_impl)
else:
    render_chatbot = _render_chatbot_impl


income, margin_data, stock_growth_data, dividend_growth_data, ratios_data, stock_prices_daily, latest_year = prepare_competitive_frames()
patent_yearly, ai_patent_yearly = prepare_patent_frames()
margin_latest = latest_metric_frame(margin_data, "ebitda_margin")
michelin_row = margin_latest[margin_latest["company"] == "Michelin"]
michelin_margin = michelin_row.iloc[0]["ebitda_margin"] if not michelin_row.empty else None
margin_rank = margin_latest.reset_index(drop=True)
michelin_rank = margin_rank.index[margin_rank["company"] == "Michelin"]
michelin_rank_text = f"#{int(michelin_rank[0]) + 1}" if len(michelin_rank) else "N/A"

st.markdown(ARTICLE_CSS, unsafe_allow_html=True)
st.markdown(get_hero_bg_css(), unsafe_allow_html=True)

# ── Right-side chat sidebar ──────────────────────────────────────────────────
with st.sidebar:
    st.markdown("<div class='chat-panel'>", unsafe_allow_html=True)
    render_chatbot()
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("<div class='article-shell'>", unsafe_allow_html=True)
st.markdown(
    "<div class='hero-banner'>"
    "<div class='hero-overlay'></div>"
    "<div class='hero-content'>"
    "<div class='eyebrow'>Wheel Street</div>"
    "<h1 class='hero-title'>Does Michelin have a strong competitive moat?</h1>"
    "<div class='hero-deck'>Goal: test whether Michelin's edge is truly durable by examining the signals a strong business should leave behind: superior margins, disciplined capital allocation, shareholder returns, and innovation versus the same global peer set.</div>"
    "</div>"
    "</div>",
    unsafe_allow_html=True,
)

st.markdown("<h2 class='section-title'>Does Michelin have a strong competitive moat?</h2>", unsafe_allow_html=True)
st.markdown(
    "<div class='section-deck' style='max-width:none;width:100%;box-sizing:border-box;background:#f8f8f8;border:1px solid #ececec;padding:1.1rem 1.2rem;border-radius:8px;white-space:normal;overflow-x:hidden;overflow-y:hidden;'>"
    "<div style='font-family:Libre Baskerville, serif;font-size:1.22rem;margin-bottom:0.5rem;'><strong>Thesis</strong></div>"
    "<div style='margin-bottom:0.6rem;'>Companies with strong competitive moats and disciplined management tend to show the following traits:</div>"
    "<ol style='margin:0.1rem 0 1rem 1.35rem;padding:0;line-height:1.45;white-space:normal;'>"
    "<li>Higher margins than peers.</li>"
    "<li>Exceptional return on invested capital (ROIC).</li>"
    "<li>Increasing shareholder returns through stock price appreciation and dividend growth.</li>"
    "<li>Sustained revenue and profit growth driven by operational excellence and innovation.</li>"
    "<li>Prolific patent and innovation funnels — highly competitive companies continuously invest in IP. In recent years, AI patents have become an increasingly important signal of a company's ability to adapt to and capitalise on changing technology.</li>"
    "</ol>"
    "<div style='font-family:Libre Baskerville, serif;font-size:1.22rem;margin:0.25rem 0 0.5rem;'><strong>Methodology</strong></div>"
    "<ul style='margin:0.1rem 0 1rem 0.25rem;padding:0;line-height:1.45;white-space:normal;list-style:none;'>"
    "<li><span style='color:#666;margin-right:0.5rem;'>•</span><strong>Companies:</strong> Michelin, Bridgestone, Goodyear, Continental, Pirelli, Sumitomo.</li>"
    "<li><span style='color:#666;margin-right:0.5rem;'>•</span><strong>Sources:</strong> Curated income statement, cash flow, ratio, and stock price datasets; supporting transcripts, filings, and news for context.</li>"
    "<li><span style='color:#666;margin-right:0.5rem;'>•</span><strong>Timelines:</strong> Financial comparisons use 10-year history plus 2025 snapshots; stock views include yearly OHLC from daily adjusted-close data.</li>"
    "</ul>"
    "<div style='font-family:Libre Baskerville, serif;font-size:1.22rem;margin:0.25rem 0 0.5rem;'><strong>Conclusion</strong></div>"
    "<ul style='margin:0.1rem 0 0 0.25rem;padding:0;line-height:1.45;white-space:normal;list-style:none;text-align:left;'>"
    "<li style='display:flex;align-items:flex-start;gap:0.55rem;white-space:normal;'><span style='color:#6e9f76;font-weight:700;display:inline-flex;align-items:center;justify-content:center;min-width:1.15rem;line-height:1;font-size:1.02rem;margin-top:0.08rem;'>✓</span><span>Michelin consistently posts the highest margins among peers, suggesting a differentiated competitive edge.</span></li>"
    "<li style='display:flex;align-items:flex-start;gap:0.55rem;white-space:normal;'><span style='color:#6e9f76;font-weight:700;display:inline-flex;align-items:center;justify-content:center;min-width:1.15rem;line-height:1;font-size:1.02rem;margin-top:0.08rem;'>✓</span><span>Michelin appears to demonstrate strong capital discipline, with the second-most efficient capital deployment among peers.</span></li>"
    "<li style='display:flex;align-items:flex-start;gap:0.55rem;white-space:normal;'><span style='color:#6e9f76;font-weight:700;display:inline-flex;align-items:center;justify-content:center;min-width:1.15rem;line-height:1;font-size:1.02rem;margin-top:0.08rem;'>✓</span><span>Michelin has delivered steady long-run dividend growth, though some competitors, including Sumitomo and Pirelli, have shown stronger stock price growth.</span></li>"
    "<li style='display:flex;align-items:flex-start;gap:0.55rem;white-space:normal;'><span style='color:#b06565;font-weight:700;display:inline-flex;align-items:center;justify-content:center;min-width:1.15rem;line-height:1;font-size:1.02rem;margin-top:0.08rem;'>✗</span><span>Michelin appears to lag in revenue growth, which weighs on profit growth and may indicate challenges in capturing share through innovation or M&amp;A.</span></li>"
    "<li style='display:flex;align-items:flex-start;gap:0.55rem;white-space:normal;'><span style='color:#b06565;font-weight:700;display:inline-flex;align-items:center;justify-content:center;min-width:1.15rem;line-height:1;font-size:1.02rem;margin-top:0.08rem;'>✗</span><span>Michelin lags competitors in patent application filings per year and appears to be behind peers in AI-related patent activity, suggesting a potential gap in innovation pipeline intensity.</span></li>"
    "</ul>"
    "</div>",
    unsafe_allow_html=True,
)

# When open: split layout (analytics wide left, sticky chat right). When closed: full width.
_tab_ctx = st.container()

with _tab_ctx:
    tabs = st.tabs(["Overview", "EBITDA Margin", "ROIC", "Dividend Growth", "Annual Stock Growth", "Revenue Growth", "EBITDA Growth", "Patents", "AI Patents"])
    with tabs[0]:
        render_overview_rankings(
            ratios_data,
            margin_data,
            income,
            stock_growth_data,
            dividend_growth_data,
            patent_yearly,
            ai_patent_yearly,
        )
    with tabs[1]:
        render_metric_tab(
            "EBITDA Margin",
            "EBITDA margin ranking on the left, followed by the top two peers and Michelin over time.",
            margin_data,
            "ebitda_margin",
        )
    with tabs[2]:
        render_metric_tab(
            "ROIC",
            "Return on invested capital (ROIC) ranking on the left, followed by the top two peers and Michelin over time.",
            ratios_data,
            "return_on_inv_capital",
        )
    with tabs[3]:
        render_metric_tab(
            "Dividend Growth",
            "Year-over-year growth in dividends paid based on cf_dvd_paid (absolute cash outflow).",
            dividend_growth_data,
            "dividend_growth",
        )
    with tabs[4]:
        render_metric_tab(
            "Annual Stock Growth",
            "Year-over-year stock price growth based on split-adjusted year-end close.",
            stock_growth_data,
            "annual_stock_growth",
        )
    with tabs[5]:
        render_metric_tab(
            "Revenue Growth",
            "Year-over-year revenue growth based on sales revenue turnover.",
            income,
            "revenue_growth",
        )
    with tabs[6]:
        render_metric_tab(
            "EBITDA Growth",
            "Year-over-year EBITDA growth based on annual EBITDA values.",
            income,
            "ebitda_growth",
        )
    with tabs[7]:
        render_patent_tab(
            patent_yearly,
            "patent_count",
            "Patent Applications per Year",
            "Annual USPTO patent applications per company, ranked by 10-year median.",
            "patents",
        )
    with tabs[8]:
        render_patent_tab(
            ai_patent_yearly,
            "ai_patent_count",
            "AI Patent Applications per Year",
            "Annual AI-driven patent applications (LLM-classified), ranked by 10-year median.",
            "ai_patents",
        )

st.markdown("</div>", unsafe_allow_html=True)
