# 🏎️ Wheel Street

Wheel Street is an interview-ready application that evaluates whether Michelin has a durable competitive moat relative to major tire peers. It combines a financial comparison dashboard, company-level evidence, and a LangGraph-powered analyst that can answer grounded questions using local financial and text data.

## Start Here

If you are reviewing this project for an interview, this README is the best entry point:

1. Understand the core question and conclusion in [docs/01_project_brief.md](docs/01_project_brief.md).
2. Review the underlying datasets and coverage in [docs/02_data_sources.md](docs/02_data_sources.md).
3. See how the system is structured in [docs/03_system_architecture.md](docs/03_system_architecture.md).
4. Review implementation choices in [docs/04_tech_stack.md](docs/04_tech_stack.md).
5. Inspect the analytical approach in [docs/05_analytics.md](docs/05_analytics.md).
6. Review the AI workflows in [docs/06_agents.md](docs/06_agents.md).

## Documentation Guide

| Topic | What It Covers | Link |
|------|------|------|
| 01 Project Brief | Objective question, thesis, method, conclusion, and success criteria | [docs/01_project_brief.md](docs/01_project_brief.md) |
| 02 Data Sources | Source systems, company coverage, timelines, gaps, and ETL reference | [docs/02_data_sources.md](docs/02_data_sources.md) |
| 03 System Architecture | End-to-end flow, package structure, runtime components, and rationale | [docs/03_system_architecture.md](docs/03_system_architecture.md) |
| 04 Tech Stack | Application, AI, data, and deployment stack with tool choices | [docs/04_tech_stack.md](docs/04_tech_stack.md) |
| 05 Analytics | Financial analytics, patent analytics, metrics, and comparison logic | [docs/05_analytics.md](docs/05_analytics.md) |
| 06 Agents | Financial analyst and patent analyst workflows, toolchains, and response behavior | [docs/06_agents.md](docs/06_agents.md) |

## Review Summary

### 01. Project Brief
The project asks a focused question: does Michelin exhibit a stronger competitive moat than peers? The working thesis is that durable moats show up in margin strength, capital efficiency, shareholder returns, and sustained growth. The app tests that thesis through a six-company comparison set and interactive drilldowns.

### 02. Data Sources
The application uses snapshot-based financial, market, transcript, news, and patent-related datasets. Core financial data comes from ROIC.ai, while patent analytics are built on USPTO-derived data. ETL is organized so extract, transform, and load stages are clearly separated and rerunnable.

### 03. System Architecture
The system uses a simple but defensible structure: Streamlit for the interface, Plotly for analytics, LangGraph for the agent loop, and DuckDB/local JSON for evidence storage. This keeps the demo stable while still showing practical agentic architecture and local data grounding.

### 04. Tech Stack
The stack is intentionally pragmatic: Python, Streamlit, Plotly, Pandas, DuckDB, LangChain, LangGraph, Docker, and Render. Each choice optimizes for interview signal, development speed, and reproducibility rather than maximum framework complexity.

### 05. Analytics
The financial analytics section compares Michelin against peers using EBITDA Margin, ROIC, Dividend Growth, Annual Stock Growth, Revenue Growth, and EBITDA Growth. The patent analytics section is structured as a second analytical track, with ingestion and summarization already in place for future UI expansion.

### 06. Agents
The financial analyst agent uses a tool-calling workflow to answer questions with quantitative evidence from local data. A patent analyst structure is also documented, showing how the project can extend beyond financials into innovation analysis using the same evidence-first design pattern.

## Companies Analyzed

| Company | Ticker | Country |
|---------|--------|---------|
| Michelin | MGDDY | France |
| Goodyear | GT | USA |
| Bridgestone | BRDCY | Japan |
| Continental | CTTAY | Germany |
| Pirelli | PLLIF | Italy |
| Sumitomo | SSUMY | Japan |

## What It Does

### 📊 Financial Dashboard
Interactive charts comparing revenue, margins, ROIC/ROE/ROA, free cash flow, dividends, and stock price performance across all six companies. Filters for year range and company selection.

### 🏢 Company Profiles
Deep dive into each company with profile information, key financial tables, recent news articles, and latest earnings call transcripts.

### 🤖 AI Financial Analyst
A LangGraph-powered conversational agent that answers questions about the tire industry by querying pre-loaded financial data. Uses a Plan → Research → Analyze workflow with 6 custom tools:

- `get_financials` — Income statement and cash flow metrics
- `get_ratios` — ROIC, ROE, ROA, margins
- `search_transcripts` — Keyword search through earnings calls
- `search_news` — Search recent news articles
- `get_stock_performance` — Price performance over custom periods
- `get_company_overview` — Company profile with financial highlights

## Why This Project Is Easy To Review

- The project is organized around one clear business question.
- The documentation is numbered in reading order for interview review.
- The app runs from committed local data snapshots, so behavior is reproducible.
- The AI layer is grounded in explicit tools and local evidence rather than vague freeform prompting.

## Architecture

```
┌────────────────────────────────────┐
│         Streamlit Frontend         │
│  ┌──────┐ ┌────────┐ ┌──────────┐ │
│  │ Home │ │Dashbrd │ │Profiles  │ │
│  │      │ │(Plotly)│ │          │ │
│  └──────┘ └────────┘ └──────────┘ │
│  ┌─────────────────────────────┐   │
│  │     AI Analyst (Chat UI)    │   │
│  └──────────┬──────────────────┘   │
└─────────────┼──────────────────────┘
              │
   ┌──────────▼──────────┐
   │   LangGraph Agent   │
   │ ┌──────┐  ┌───────┐ │
   │ │Agent │→ │ Tools │←┤──→ Pre-downloaded
   │ │(LLM) │← │ Node  │ │    JSON data
   │ └──────┘  └───────┘ │
   └──────────┬──────────┘
              │
        ┌─────▼─────┐
        │  OpenAI   │
        │  GPT-4o   │
        └───────────┘
```

## Data Sources

All financial data is sourced from [roic.ai](https://roic.ai) REST API:
- Company profiles and descriptions
- 10 years of annual income statements and cash flows
- Profitability ratios (ROIC, ROE, ROA, margins)
- ~5 years of daily stock price history
- Recent news articles (50 per company)
- Latest earnings call transcripts

Data is pre-downloaded and committed to the repository as JSON files for offline use and fast load times.

## Quick Start

### Option 1: Docker (Recommended)

```bash
git clone https://github.com/gregf-ai/Michelin-GregF.git
cd Michelin-GregF

# Build and run
docker build -t wheel-street .
docker run -p 8501:8501 -e OPENAI_API_KEY=your-key-here wheel-street
```

Open http://localhost:8501

### Option 2: Local Python

```bash
git clone https://github.com/gregf-ai/Michelin-GregF.git
cd Michelin-GregF

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Set API key
set OPENAI_API_KEY=your-key-here  # Windows
# export OPENAI_API_KEY=your-key-here  # macOS/Linux

# Run
streamlit run app.py
```

### Option 3: Re-download data (optional)

If you want to refresh the financial data:

```bash
set ROIC_API_KEY=your-roic-key-here
python data/extract/download.py
```

### Option 4: Build DuckDB analytics store (optional)

```bash
python data/load/process_to_duckdb.py
```

This creates `data/processed/curated/financial_analyst.duckdb` with processed financial tables,
raw text tables (news/transcripts), company profiles, and summary tables.

## Deployment (Render)

This app is configured for [Render](https://render.com) free tier:

1. Push to GitHub
2. Connect repo on Render dashboard → New Web Service → Docker
3. Set environment variable: `OPENAI_API_KEY`
4. Deploy

The `render.yaml` file now lives at the repo root, so Render can use it directly.

## Design Decisions

- **Pre-downloaded data**: Financial data is committed as JSON to avoid API dependencies at runtime, ensure fast load times, and keep the app functional even without a roic.ai API key.
- **LangGraph over simple chains**: The agent architecture (Plan → Research → Analyze loop) demonstrates agentic AI capabilities — the agent decides which tools to call and iterates until it has enough data.
- **gpt-4o-mini default**: Balances capability with cost. The model can be changed via `OPENAI_MODEL` env var.
- **Streamlit**: Fastest path to a polished, interactive data app with minimal frontend code.
- **Docker + Render**: Simple, portable deployment that's easy to reproduce locally.
- **6 companies**: Added Pirelli and Sumitomo beyond the required 4 to provide a more comprehensive industry comparison.

## Limitations & Future Improvements

- **Static data**: Data is a snapshot from the download date; no live refresh (intentional for demo reliability).
- **ADR tickers**: Some companies trade as ADRs (MGDDY, BRDCY, CTTAY, PLLIF, SSUMY), which may not perfectly reflect local exchange pricing.
- **Transcript availability**: Sumitomo (SSUMY) has no earnings transcript available via the API.
- **Currency normalization**: Financial statements are in each company's reporting currency. Cross-company dollar comparisons may be affected by exchange rates.
- **Future enhancements**: Add quarterly data views, sector benchmarking, live data refresh, and PDF report export.

## Tech Stack

- **Frontend**: Streamlit
- **Charts**: Plotly
- **AI Agent**: LangGraph + LangChain
- **LLM**: OpenAI GPT-4o-mini
- **Data**: roic.ai REST API
- **Deployment**: Docker → Render
