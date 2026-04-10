# System Architecture

## High-Level Flow
1. ETL pulls and normalizes source data into local `data/` assets.
2. `data/load/process_to_duckdb.py` materializes indexed analytics tables in DuckDB.
3. Streamlit app renders comparison visuals and sends chat requests.
4. FastAPI service exposes `/qa`, `/search/*`, `/query/financial-sql`, and `/data/coverage`.
5. LangChain-based router classifies intent (`financial`, `transcript`, `patent`, `mixed`) and binds a route-specific tool subset.
6. Tools fetch structured evidence from DuckDB and curated snapshots.
7. Agent synthesizes responses with quantitative support, citations, and explicit data-gap notes.

## Package Structure
- `app.py`: UI composition, tab logic, chart interactions, chat panel
- `src/data_loader.py`: data loading helpers
- `src/charts.py`: chart-building utilities
- `src/tools.py`: LangChain tool implementations, including DuckDB-backed transcript retrieval
- `src/graph.py`: LangChain orchestration with explicit router node and tool subset mapping
- `api_service/main.py`: hosted API endpoints and QA evidence extraction
- `api_service/schemas.py`: request/response contracts (`tool_trace`, `citations`, etc.)
- `data/`: ETL scripts, raw snapshots, processed curated outputs

## Runtime Components
- UI: Streamlit
- Visualization: Plotly
- API Layer: FastAPI (`/`, `/health`, `/data/coverage`, `/query/financial-sql`, `/search/transcripts`, `/search/patents`, `/qa`)
- Agent Orchestration: LangChain (router -> agent -> tools -> agent loop)
- Local Analytics Store: DuckDB (`data/processed/curated/financial_analyst.duckdb`)
- LLM: OpenAI model via `OPENAI_API_KEY`

## Why This Shape
- Snapshot-first data keeps demos stable and reproducible.
- Hosted API boundary keeps UI and agent runtime independently deployable.
- Router-based tool binding reduces irrelevant tool calls and improves reliability.
- Modular code layout keeps interview discussion clear by responsibility.
