# System Architecture

## High-Level Flow
1. ETL pulls and normalizes source data into local `data/` assets.
2. Streamlit app loads curated tables and renders comparison visuals.
3. LangGraph-powered analyst agent routes user questions to tools.
4. Tools fetch structured evidence from local files and DuckDB.
5. Agent synthesizes responses with quantitative support and caveats.

## Package Structure
- `app.py`: UI composition, tab logic, chart interactions, chat panel
- `src/data_loader.py`: data loading helpers
- `src/charts.py`: chart-building utilities
- `src/tools.py`: LangChain tool implementations for financial retrieval and SQL
- `src/graph.py`: LangGraph orchestration and model/tool loop
- `data/`: ETL scripts, raw snapshots, processed curated outputs

## Runtime Components
- UI: Streamlit
- Visualization: Plotly
- Agent Orchestration: LangGraph + LangChain
- Local Analytics Store: DuckDB (`data/processed/curated/financial_analyst.duckdb`)
- LLM: OpenAI model via `OPENAI_API_KEY`

## Why This Shape
- Snapshot-first data keeps demos stable and reproducible.
- Tool-calling agent architecture demonstrates practical AI orchestration.
- Modular code layout keeps interview discussion clear by responsibility.
