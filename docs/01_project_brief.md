# Project Brief

## Objective
Build an interactive application that compares the financial performance of major tire companies and supports question answering with an agentic LLM workflow.

## Companies in Scope
- Michelin (MGDDY)
- Goodyear (GT)
- Bridgestone (BRDCY)
- Continental (CTTAY)
- Pirelli (PLLIF)
- Sumitomo (SSUMY)

## Core User Flows
1. Compare financials on the dashboard.
2. Inspect company-specific profiles, news, and transcripts.
3. Ask natural-language analysis questions in the Financial Analyst agent.

## Data Scope
- Income statements and cash flows (15 annual periods)
- Profitability ratios (15 annual periods)
- Historical stock prices (~10 years where available)
- News (last ~5 years via pagination)
- Earnings transcripts (all available from 2021 onward)

## Done Criteria (Interview-Ready)
- App runs locally and in Docker.
- App deploys on Render free tier.
- Dashboard and profile pages load with all 6 companies.
- AI Analyst answers benchmark questions with numeric citations.
- README and docs clearly explain architecture, tradeoffs, and limitations.

## Non-Goals (for this assessment window)
- Real-time streaming data refresh
- Full FX precision pipeline with external historical forex API
- Full enterprise auth and multi-user state
