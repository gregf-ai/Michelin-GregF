import os
import traceback
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
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
    max-width: 1360px;
    padding-top: 2.5rem;
    padding-bottom: 4rem;
}

body, .stMarkdown, .stCaption, .stText, .stTabs, .stMetric {
    font-family: 'IBM Plex Sans', sans-serif;
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
    font-size: 0.78rem;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: var(--muted);
    margin-bottom: 0.9rem;
}

.hero-title {
    font-size: clamp(2.6rem, 4vw, 4.5rem);
    line-height: 1.05;
    margin: 0 0 1rem 0;
    max-width: 12ch;
}

.hero-deck {
    max-width: 60ch;
    font-size: 1.1rem;
    line-height: 1.8;
    color: #303030;
    margin-bottom: 1.75rem;
}

.section-title {
    margin-top: 1rem;
    margin-bottom: 0.65rem;
    font-size: 2rem;
}

.section-deck {
    max-width: 58ch;
    font-size: 1rem;
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
    font-size: 0.72rem;
}

.kicker-value {
    font-family: 'Libre Baskerville', serif;
    font-size: 1.6rem;
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
    font-size: 0.88rem;
    margin-bottom: 0.6rem;
}

div[data-baseweb="tab-list"] {
    gap: 0.4rem;
}

button[data-baseweb="tab"] {
    background: #f2f2f2;
    border-radius: 0;
    border: 1px solid #dddddd;
    padding: 0.6rem 0.9rem;
}

button[data-baseweb="tab"][aria-selected="true"] {
    background: #111111;
    color: #ffffff;
    border-color: #111111;
}

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
}
</style>
"""

GRAYSCALE = ["#111111", "#555555", "#8c8c8c", "#b4b4b4", "#d0d0d0", "#e5e5e5"]
PEER_ORDER = [COMPANY_NAMES[t] for t in COMPANY_NAMES]
CURATED_DIR = Path(__file__).resolve().parent / "data" / "processed" / "curated"
ENV_FILE_PATH = Path(__file__).resolve().parent / ".env"


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
def prepare_competitive_frames() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, int]:
    income = pd.read_csv(CURATED_DIR / "income_statements_usd.csv")
    stock_prices = pd.read_csv(CURATED_DIR / "stock_prices.csv")
    cash_flows = pd.read_csv(CURATED_DIR / "cash_flows_usd.csv")

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

    latest_year = int(margin["fiscal_year"].max()) if not margin.empty else 0
    return income, margin, year_end_prices, cash_flows, latest_year


def latest_metric_frame(df: pd.DataFrame, metric: str) -> pd.DataFrame:
    year = get_latest_metric_year(df, metric)
    if year is None:
        return pd.DataFrame(columns=df.columns)

    latest = df[(df["fiscal_year"] == year) & (~df[metric].isna())].copy()
    latest["company"] = pd.Categorical(latest["company"], categories=PEER_ORDER, ordered=True)
    return latest.sort_values(metric, ascending=False)


def median_metric_frame(df: pd.DataFrame, metric: str) -> pd.DataFrame:
    median = (
        df.dropna(subset=[metric])
        .groupby("company", as_index=False)[metric]
        .median()
    )
    median["company"] = pd.Categorical(median["company"], categories=PEER_ORDER, ordered=True)
    return median.sort_values(metric, ascending=False)


def build_rank_bar(df: pd.DataFrame, metric: str) -> go.Figure:
    ranked = latest_metric_frame(df, metric)
    colors = GRAYSCALE[: len(ranked)]
    fig = go.Figure(
        go.Bar(
            x=ranked[metric],
            y=ranked["company"],
            orientation="h",
            marker=dict(color=colors, line=dict(color="#111111", width=0)),
            customdata=ranked[["company"]],
            text=[format_pct(v) for v in ranked[metric]],
            textposition="outside",
            cliponaxis=False,
            hovertemplate="%{y}: %{x:.1f}%<extra></extra>",
        )
    )
    fig.update_layout(
        height=360,
        margin=dict(l=0, r=50, t=8, b=8),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False, title=""),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=True, title="", tickfont=dict(size=13, color="#111111"), autorange="reversed"),
    )
    return fig


def build_top3_trend(df: pd.DataFrame, metric: str) -> go.Figure:
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
        height=360,
        margin=dict(l=8, r=12, t=8, b=8),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(x=1.01, y=0.5, xanchor="left", yanchor="middle", bgcolor="rgba(0,0,0,0)", borderwidth=0, font=dict(size=12)),
        xaxis=dict(showgrid=False, title="", tickfont=dict(size=11, color="#666666")),
        yaxis=dict(showgrid=True, gridcolor="#ececec", zeroline=False, showticklabels=False, title=""),
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
        height=360,
        margin=dict(l=8, r=12, t=44, b=8),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        title=dict(text=company, x=0.0, xanchor="left", y=0.98, yanchor="top", font=dict(size=15, color="#111111"), pad=dict(t=2, b=0)),
        xaxis=dict(showgrid=False, title="", tickfont=dict(size=11, color="#666666")),
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


def render_metric_tab(title: str, note: str, df: pd.DataFrame, metric: str) -> None:
    compare_year = get_latest_metric_year(df, metric)
    ranked = latest_metric_frame(df, metric)
    missing = [c for c in PEER_ORDER if c not in set(ranked["company"]) ]

    year_note = f"Comparison year: {compare_year}." if compare_year is not None else "Comparison year unavailable."
    if missing:
        year_note += " Missing in this year: " + ", ".join(missing) + "."

    st.markdown(f"<div class='chart-note'>{note} {year_note}</div>", unsafe_allow_html=True)
    chart_left, chart_right = st.columns([1, 1.35], gap="large")
    with chart_left:
        selection = st.plotly_chart(
            build_rank_bar(df, metric),
            width="stretch",
            config={"displayModeBar": False},
            key=f"rank_{title.lower().replace(' ', '_')}",
            on_select="rerun",
            selection_mode="points",
        )
    with chart_right:
        selected_company = extract_selected_company(selection)
        if selected_company:
            st.plotly_chart(
                build_company_history_bar(df, metric, selected_company),
                width="stretch",
                config={"displayModeBar": False},
            )
        else:
            st.plotly_chart(build_top3_trend(df, metric), width="stretch", config={"displayModeBar": False})


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


income, margin_data, stock_growth_data, dividend_growth_data, latest_year = prepare_competitive_frames()
margin_latest = latest_metric_frame(margin_data, "ebitda_margin")
michelin_row = margin_latest[margin_latest["company"] == "Michelin"]
michelin_margin = michelin_row.iloc[0]["ebitda_margin"] if not michelin_row.empty else None
margin_rank = margin_latest.reset_index(drop=True)
michelin_rank = margin_rank.index[margin_rank["company"] == "Michelin"]
michelin_rank_text = f"#{int(michelin_rank[0]) + 1}" if len(michelin_rank) else "N/A"

st.markdown(ARTICLE_CSS, unsafe_allow_html=True)
st.markdown("<div class='article-shell'>", unsafe_allow_html=True)
st.markdown("<div class='eyebrow'>Michelin Peer Analysis</div>", unsafe_allow_html=True)
st.markdown("<h1 class='hero-title'>How competitive is Michelin compared to peers?</h1>", unsafe_allow_html=True)
st.markdown(
    f"<div class='hero-deck'>This page is structured like a research note rather than a dashboard. The first section isolates Michelin’s operating competitiveness against the same six-company tire peer set already loaded in the app. The visual treatment is intentionally stripped back: black, gray, white, minimal scaffolding, and only the comparisons that matter.</div>",
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

st.markdown("<h2 class='section-title'>How competitive is Michelin compared to peers?</h2>", unsafe_allow_html=True)
st.markdown(
    "<div class='section-deck'>The left side provides the financial figures and visual evidence. The right side keeps a financial analyst agent available in-line for follow-up questions, so analysis happens directly beside the charts.</div>",
    unsafe_allow_html=True,
)

left_col, right_col = st.columns([1.55, 0.95], gap="large")
with left_col:
    tabs = st.tabs(["Overview", "Margin", "Revenue Growth", "EBITDA Growth", "Annual Stock Growth", "Dividend Growth"])
    with tabs[0]:
        st.markdown(
            "<div class='tbd-card'><strong>Written overview</strong><br><br>This tab is reserved for the narrative summary that will synthesize Michelin’s competitive standing. The chart tabs already use live data, so this narrative can be added later without changing the page structure.</div>",
            unsafe_allow_html=True,
        )
    with tabs[1]:
        render_metric_tab(
            "Margin",
            "Latest-year EBITDA margin ranking on the left, followed by the top three companies’ EBITDA margin trend over time.",
            margin_data,
            "ebitda_margin",
        )
    with tabs[2]:
        render_metric_tab(
            "Revenue Growth",
            "Year-over-year revenue growth based on is_sales_revenue_turnover.",
            income,
            "revenue_growth",
        )
    with tabs[3]:
        render_metric_tab(
            "EBITDA Growth",
            "Year-over-year EBITDA growth based on annual EBITDA values.",
            income,
            "ebitda_growth",
        )
    with tabs[4]:
        render_metric_tab(
            "Annual Stock Growth",
            "Year-over-year stock price growth based on split-adjusted year-end close (adj_close).",
            stock_growth_data,
            "annual_stock_growth",
        )
    with tabs[5]:
        render_metric_tab(
            "Dividend Growth",
            "Year-over-year growth in dividends paid based on cf_dvd_paid (absolute cash outflow).",
            dividend_growth_data,
            "dividend_growth",
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
