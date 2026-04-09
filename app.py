import base64
import os
import traceback
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError
from langchain_core.messages import AIMessage, HumanMessage

from src.data_loader import COMPANY_NAMES
from src.graph import build_graph

st.set_page_config(
    page_title="Wheel Street",
    page_icon="●",
    layout="wide",
    initial_sidebar_state="collapsed",
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

[data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stSidebar"] {
    display: none;
}

[data-testid="block-container"] {
    max-width: 1560px;
    padding-top: 2.5rem;
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
    padding: 2.25rem 2.5rem 2.75rem;
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
    background: linear-gradient(180deg, #171717 0%, #101010 100%);
    border: 1px solid #303030;
    border-radius: 18px;
    box-shadow: 0 20px 44px rgba(0,0,0,0.22);
    padding: 1rem 1rem 0.75rem;
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

.chat-panel [data-testid="stChatMessage"] {
    background: transparent;
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
    color: #222222;
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
    min-height: 340px;
    background-size: cover;
    background-position: center 35%;
    margin: -2.25rem -2.5rem 2rem -2.5rem;
    overflow: hidden;
}

.hero-overlay {
    position: absolute;
    inset: 0;
    background: linear-gradient(120deg, rgba(0,0,0,0.82) 0%, rgba(0,0,0,0.48) 55%, rgba(0,0,0,0.18) 100%);
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
</style>
"""

GRAYSCALE = ["#111111", "#555555", "#8c8c8c", "#b4b4b4", "#d0d0d0", "#e5e5e5"]
PEER_ORDER = [COMPANY_NAMES[t] for t in COMPANY_NAMES]
CURATED_DIR = Path(__file__).resolve().parent / "data" / "processed" / "curated"
ENV_FILE_PATH = Path(__file__).resolve().parent / ".env"
HERO_IMG_PATH = Path(__file__).resolve().parent / "static" / "bull.jpg"


def get_hero_bg_css() -> str:
    if HERO_IMG_PATH.exists():
        b64 = base64.b64encode(HERO_IMG_PATH.read_bytes()).decode()
        return f"<style>.hero-banner {{ background-image: url('data:image/jpeg;base64,{b64}'); }}</style>"
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
def prepare_competitive_frames() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, int]:
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

    ratios["fiscal_year"] = pd.to_numeric(ratios["fiscal_year"], errors="coerce")
    ratios = ratios.dropna(subset=["fiscal_year", "return_on_inv_capital", "company"]).sort_values(["company", "fiscal_year"])

    latest_year = int(margin["fiscal_year"].max()) if not margin.empty else 0
    return income, margin, year_end_prices, cash_flows, ratios, latest_year


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
    if rank is None:
        return "⚪"
    if rank == 1:
        return "✅"
    if rank <= 3:
        return "🟢"
    return "❌"


def render_overview_rankings(metric_specs: list[tuple[str, str, pd.DataFrame, str]]) -> None:
    items: list[dict[str, object]] = []
    for label, description, df, metric in metric_specs:
        ranked = median_metric_frame(df, metric).reset_index(drop=True)
        rows = ranked.index[ranked["company"] == "Michelin"]
        rank = int(rows[0]) + 1 if len(rows) else None
        leader = str(ranked.iloc[0]["company"]) if not ranked.empty else None
        items.append({
            "label": label,
            "description": description,
            "rank": rank,
            "leader": leader,
        })

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
            leader_note = f" Leader: {item['leader']}."

        lines.append(
            "<div class='overview-line'>"
            f"<div class='overview-left'>{emoji} {rank_text}</div>"
            f"<div class='overview-main'><strong>{item['label']}</strong>: {item['description']}{leader_note}</div>"
            "</div>"
        )

    st.markdown(
        "<div class='overview-panel'>"
        "<div class='overview-head'>Michelin Competitive Scorecard</div>"
        "<div class='overview-subhead'>Sorted by Michelin rank (best to worst). Basis: 10-year median.</div>"
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
        
        # Optimize y-axis range for better chart height
        value_range = max(y_vals) - min(y_vals)
        y_spread = max(value_range * 0.6, abs(max(y_vals) - center_val), abs(min(y_vals) - center_val)) * 1.3

        # Add area shading between data and center line
        fig.add_trace(go.Scatter(
            x=x_vals + x_vals[::-1],
            y=[max(v, center_val) for v in y_vals] + [center_val] * len(y_vals),
            fill="toself",
            fillcolor=shading_color_above,
            line_width=0,
            showlegend=False,
            hoverinfo="skip",
        ), row=row, col=1)

        fig.add_trace(go.Scatter(
            x=x_vals + x_vals[::-1],
            y=[min(v, center_val) for v in y_vals] + [center_val] * len(y_vals),
            fill="toself",
            fillcolor=shading_color_below,
            line_width=0,
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
                showarrow=False, yshift=8,
                font=dict(size=9, color="#666666"),
            )

        # Company name and final value annotation on right
        val_series = cdf[cdf["fiscal_year"] == 2025][metric]
        val_str = format_pct(val_series.iloc[0]) if not val_series.empty else format_pct(y_vals[-1])
        fig.add_annotation(
            xref="paper", yref=yaxis_refs[i],
            x=1.02, y=y_vals[-1],
            text=f"<b>{company}</b><br>{val_str}",
            showarrow=False, xanchor="left", yanchor="middle",
            font=dict(size=14, color="#111111"),
        )
        
        # Label with leader line for center value on left
        if is_growth_metric:
            # For 0 line, just add leader line
            fig.add_annotation(
                xref="paper", yref=yaxis_refs[i],
                x=-0.19, y=center_val,
                ax=-30, ay=0,
                showarrow=True, arrowhead=2, arrowsize=0.8, arrowwidth=0.5, arrowcolor="#999999",
                text="",
            )
        else:
            # For median, show label with leader line
            fig.add_annotation(
                xref="paper", yref=yaxis_refs[i],
                x=-0.19, y=center_val,
                ax=-30, ay=0,
                showarrow=True, arrowhead=2, arrowsize=0.8, arrowwidth=0.5, arrowcolor="#999999",
                text=f"<span style='font-size: 11px; color: #666666;'>median {center_label}</span>",
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
        height=580,
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
        title=dict(text=company, x=0.0, xanchor="left", y=0.98, yanchor="top", font=dict(size=19, color="#111111"), pad=dict(t=2, b=0)),
        xaxis=dict(showgrid=False, title="", tickfont=dict(size=15, color="#666666")),
        yaxis=dict(showgrid=True, gridcolor="#ececec", zeroline=False, showticklabels=False, title=""),
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
    michelin_history = df[df["company"] == "Michelin"].dropna(subset=[metric]).sort_values("fiscal_year")[metric].tolist()
    trend = "increasing" if len(michelin_history) > 1 and michelin_history[-1] > michelin_history[0] else "decreasing"

    rank_str = f"#{rank}" if rank else "N/A"
    leader_str = f"led by {leader}" if leader and leader != "Michelin" else ""
    median_str = f"{format_pct(median_val)}" if median_val is not None else "N/A"
    val_2025_str = f"{format_pct(val_2025)}" if val_2025 is not None else "N/A"
    leader_clause = f" Peers are {leader_str}." if leader_str else ""

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
    st.markdown(f"**Analysis:** {analysis}", unsafe_allow_html=True)

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

    chart_left, chart_right = st.columns([1, 1.35], gap="large")
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
    with chart_right:
        st.markdown(f"**Top 2 + Michelin Over Time**", unsafe_allow_html=True)
        selected_company = extract_selected_company(selection)
        if selected_company:
            st.plotly_chart(
                build_company_history_bar(df, metric, selected_company),
                width="stretch",
                config={"displayModeBar": False},
            )
        else:
            others = [c for c in ranked["company"].tolist() if c != "Michelin"][:2]
            sparkline_companies = ["Michelin"] + others
            st.plotly_chart(build_sparkline_stack(df, metric, sparkline_companies), width="stretch", config={"displayModeBar": False, "scrollZoom": False})


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


def init_agent() -> None:
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
    if "agent" not in st.session_state:
        model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
        st.session_state.agent = build_graph(model_name=model)
    # chat_history: display-only list of (role, text) tuples — never passed raw to agent.
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []


def render_chatbot() -> None:
    init_agent()

    # Outer wrapper styled via .chat-panel CSS selector
    wrapper = st.container()
    with wrapper:
        st.markdown("#### Financial Analyst Agent")
        st.caption(
            "Ask focused questions while reviewing the figures on the left. "
            "The agent can pull financials, ratios, cash flow, news, transcripts, "
            "and DuckDB-backed comparisons."
        )

        if "agent" not in st.session_state:
            st.info("OpenAI credentials are not available — chat is offline.")
            return

        # Suggestion buttons only before the first question
        if not st.session_state.chat_history:
            suggestions = [
                "Does Michelin structurally outperform peers on margins?",
                "What explains Michelin's revenue growth versus Goodyear and Bridgestone?",
                "Which peer is most comparable to Michelin on profitability?",
            ]
            for idx, suggestion in enumerate(suggestions):
                if st.button(suggestion, key=f"single_page_suggestion_{idx}", width="stretch"):
                    st.session_state.pending_question = suggestion

        # ── Fixed-height scrollable message area ──
        has_history = bool(st.session_state.chat_history)
        chat_box = st.container(height=560 if has_history else 180, border=True)
        with chat_box:
            if has_history:
                for role, text in st.session_state.chat_history:
                    with st.chat_message(role):
                        st.markdown(text)
            else:
                st.caption("Start with a question and this panel will expand into a scrollable conversation view.")

        # ── Input bar (always at a fixed position below the container) ──
        user_input = st.chat_input("Ask about Michelin versus peers")
        if "pending_question" in st.session_state:
            user_input = st.session_state.pending_question
            del st.session_state.pending_question

        if user_input:
            st.session_state.chat_history.append(("user", user_input))

            with chat_box:
                with st.chat_message("user"):
                    st.markdown(user_input)

                with st.chat_message("assistant"):
                    with st.spinner("Researching"):
                        try:
                            clean_messages = []
                            for role, text in st.session_state.chat_history[:-1]:
                                if role == "user":
                                    clean_messages.append(HumanMessage(content=text))
                                else:
                                    clean_messages.append(AIMessage(content=text))
                            clean_messages.append(HumanMessage(content=user_input))

                            result = st.session_state.agent.invoke({"messages": clean_messages})
                            response = result["messages"][-1]
                            st.markdown(response.content)
                            st.session_state.chat_history.append(("assistant", response.content))
                        except Exception as exc:
                            tb = traceback.format_exc()
                            print(tb)
                            short = str(exc) or type(exc).__name__
                            error_msg = f"The analyst hit an error: {short}"
                            with st.expander("Error detail"):
                                st.code(tb)
                            st.error(error_msg)
                            st.session_state.chat_history.append(("assistant", error_msg))
            st.rerun()


income, margin_data, stock_growth_data, dividend_growth_data, ratios_data, latest_year = prepare_competitive_frames()
margin_latest = latest_metric_frame(margin_data, "ebitda_margin")
michelin_row = margin_latest[margin_latest["company"] == "Michelin"]
michelin_margin = michelin_row.iloc[0]["ebitda_margin"] if not michelin_row.empty else None
margin_rank = margin_latest.reset_index(drop=True)
michelin_rank = margin_rank.index[margin_rank["company"] == "Michelin"]
michelin_rank_text = f"#{int(michelin_rank[0]) + 1}" if len(michelin_rank) else "N/A"

st.markdown(ARTICLE_CSS, unsafe_allow_html=True)
st.markdown(get_hero_bg_css(), unsafe_allow_html=True)
st.markdown("<div class='article-shell'>", unsafe_allow_html=True)
st.markdown(
    "<div class='hero-banner'>"
    "<div class='hero-overlay'></div>"
    "<div class='hero-content'>"
    "<div class='eyebrow'>Wheel Street</div>"
    "<h1 class='hero-title'>Does Michelin have a strong competitive moat?</h1>"
    "<div class='hero-deck'>Goal: quantify competitive edge with evidence from income statement strength, stock performance, and patent portfolio depth across the same global peer set.</div>"
    "</div>"
    "</div>",
    unsafe_allow_html=True,
)
st.markdown(
    f"<div class='kicker-grid'>"
    f"<div class='kicker-card'><div class='kicker-label'>Latest Margin Year</div><div class='kicker-value'>{latest_year}</div></div>"
    f"<div class='kicker-card'><div class='kicker-label'>Michelin EBITDA Margin</div><div class='kicker-value'>{format_pct(michelin_margin)}</div></div>"
    f"<div class='kicker-card'><div class='kicker-label'>Michelin Rank</div><div class='kicker-value'>{michelin_rank_text}</div></div>"
    f"</div>",
    unsafe_allow_html=True,
)

st.markdown("<h2 class='section-title'>Does Michelin have a strong competitive moat?</h2>", unsafe_allow_html=True)
st.markdown(
    "<div class='section-deck'><strong>Left:</strong> Competitive metrics from income statements, cash flows, stock prices, and financial ratios across the 10-year period. <strong>Right:</strong> AI analyst with access to SEC filings (10-K, 10-Q), earnings transcripts, news feeds, and patent analytics to contextualize the numbers.</div>",
    unsafe_allow_html=True,
)

left_col, right_col = st.columns([1.55, 0.95], gap="large")
with left_col:
    tabs = st.tabs(["Overview", "EBITDA Margin", "ROIC", "Dividend Growth", "Annual Stock Growth", "Revenue Growth", "EBITDA Growth"])
    with tabs[0]:
        render_overview_rankings(
            [
                (
                    "ROIC",
                    "Return on invested capital, capturing how efficiently operating capital is converted into returns.",
                    ratios_data,
                    "return_on_inv_capital",
                ),
                (
                    "Margin",
                    "EBITDA margin, a read on operating profitability and pricing discipline.",
                    margin_data,
                    "ebitda_margin",
                ),
                (
                    "Revenue Growth",
                    "Year-over-year top-line growth to gauge demand momentum and market capture.",
                    income,
                    "revenue_growth",
                ),
                (
                    "EBITDA Growth",
                    "Year-over-year EBITDA growth as a signal of earnings power expansion.",
                    income,
                    "ebitda_growth",
                ),
                (
                    "Annual Stock Growth",
                    "Year-over-year change in split-adjusted year-end stock price as a market verdict.",
                    stock_growth_data,
                    "annual_stock_growth",
                ),
                (
                    "Dividend Growth",
                    "Growth in dividends paid, indicating payout durability and cash distribution strength.",
                    dividend_growth_data,
                    "dividend_growth",
                ),
            ]
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
with right_col:
    st.markdown("<div class='chat-panel'>", unsafe_allow_html=True)
    render_chatbot()
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("<h2 class='section-title'>How innovative is Michelin compared to their peers?</h2>", unsafe_allow_html=True)
st.markdown(
    "<div class='section-deck'>This second section is intentionally left as the next build target. The patent XML pipeline is now saving source files locally, which gives us the right raw material for the innovation section that comes next.</div>",
    unsafe_allow_html=True,
)
st.markdown("</div>", unsafe_allow_html=True)
