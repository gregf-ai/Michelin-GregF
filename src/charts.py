"""Plotly chart builders for financial comparisons."""

import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

from src.data_loader import BRAND_COLORS


def _color_map():
    return BRAND_COLORS


def revenue_comparison(df: pd.DataFrame) -> go.Figure:
    fig = px.bar(
        df, x="fiscal_year", y="is_sales_revenue_turnover", color="company",
        barmode="group", color_discrete_map=_color_map(),
        labels={"is_sales_revenue_turnover": "Revenue", "fiscal_year": "Year"},
        title="Revenue Comparison",
    )
    fig.update_layout(yaxis_tickprefix="$", yaxis_tickformat=",.0s", legend_title="")
    return fig


def margin_trends(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    for company in df["company"].unique():
        cdf = df[df["company"] == company].sort_values("fiscal_year")
        color = BRAND_COLORS.get(company, None)
        fig.add_trace(go.Scatter(
            x=cdf["fiscal_year"], y=cdf["gross_margin"],
            name=f"{company} (Gross)", mode="lines+markers",
            line=dict(color=color),
        ))
        fig.add_trace(go.Scatter(
            x=cdf["fiscal_year"], y=cdf["oper_margin"],
            name=f"{company} (Operating)", mode="lines",
            line=dict(color=color, dash="dash"),
        ))
    fig.update_layout(
        title="Gross & Operating Margin Trends",
        yaxis_title="Margin (%)", xaxis_title="Year", legend_title="",
    )
    return fig


def roic_comparison(df: pd.DataFrame) -> go.Figure:
    fig = px.line(
        df, x="fiscal_year", y="return_on_inv_capital", color="company",
        markers=True, color_discrete_map=_color_map(),
        labels={"return_on_inv_capital": "ROIC (%)", "fiscal_year": "Year"},
        title="Return on Invested Capital (ROIC)",
    )
    fig.update_layout(legend_title="")
    return fig


def roe_roa_comparison(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    for company in df["company"].unique():
        cdf = df[df["company"] == company].sort_values("fiscal_year")
        color = BRAND_COLORS.get(company, None)
        fig.add_trace(go.Scatter(
            x=cdf["fiscal_year"], y=cdf["return_com_eqy"],
            name=f"{company} (ROE)", mode="lines+markers",
            line=dict(color=color),
        ))
        fig.add_trace(go.Scatter(
            x=cdf["fiscal_year"], y=cdf["return_on_asset"],
            name=f"{company} (ROA)", mode="lines",
            line=dict(color=color, dash="dot"),
        ))
    fig.update_layout(
        title="Return on Equity & Return on Assets",
        yaxis_title="%", xaxis_title="Year", legend_title="",
    )
    return fig


def debt_equity(df: pd.DataFrame) -> go.Figure:
    fig = px.bar(
        df, x="fiscal_year", y="net_debt_to_shrhldr_eqty", color="company",
        barmode="group", color_discrete_map=_color_map(),
        labels={"net_debt_to_shrhldr_eqty": "Net Debt / Equity", "fiscal_year": "Year"},
        title="Leverage: Net Debt to Shareholder Equity",
    )
    fig.update_layout(legend_title="")
    return fig


def free_cash_flow(df: pd.DataFrame) -> go.Figure:
    fig = px.bar(
        df, x="fiscal_year", y="cf_free_cash_flow", color="company",
        barmode="group", color_discrete_map=_color_map(),
        labels={"cf_free_cash_flow": "Free Cash Flow", "fiscal_year": "Year"},
        title="Free Cash Flow",
    )
    fig.update_layout(yaxis_tickprefix="$", yaxis_tickformat=",.0s", legend_title="")
    return fig


def normalized_stock_price(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    for company in df["company"].unique():
        cdf = df[df["company"] == company].sort_values("date")
        if cdf.empty:
            continue
        first_price = cdf["adj_close"].iloc[0]
        if first_price and first_price > 0:
            cdf = cdf.copy()
            cdf["normalized"] = (cdf["adj_close"] / first_price) * 100
            color = BRAND_COLORS.get(company, None)
            fig.add_trace(go.Scatter(
                x=cdf["date"], y=cdf["normalized"],
                name=company, mode="lines", line=dict(color=color),
            ))
    fig.update_layout(
        title="Normalized Stock Price (Rebased to 100)",
        yaxis_title="Index (100 = Start)", xaxis_title="", legend_title="",
    )
    return fig


def capex_trend(df: pd.DataFrame) -> go.Figure:
    fig = px.bar(
        df, x="fiscal_year", y="cf_cap_expenditures", color="company",
        barmode="group", color_discrete_map=_color_map(),
        labels={"cf_cap_expenditures": "Capital Expenditures", "fiscal_year": "Year"},
        title="Capital Expenditures",
    )
    fig.update_layout(yaxis_tickprefix="$", yaxis_tickformat=",.0s", legend_title="")
    return fig
