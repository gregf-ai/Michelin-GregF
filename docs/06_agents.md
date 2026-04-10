# Agents

This document explains how the agent system works end-to-end in this project,
including local mode, hosted API mode, tool orchestration, evidence handling,
and the approach for large patent corpora.

## 1) Agent System Goals

The system is designed to answer questions about:

- Income statements and cash flow fundamentals
- Profitability and return ratios
- Earnings call transcript evidence
- Patent activity and AI-related filing themes

Core design goals:

- Ground answers in local data artifacts (JSON/CSV/DuckDB), not freeform generation.
- Make tool usage observable.
- Keep deployment simple enough for interview/demo use.
- Provide a path to scale patent retrieval as data volume grows.

## 2) Two Runtime Modes

The project now supports two execution modes for the chat analyst.

### Local In-Process Mode

Streamlit imports and runs the LangChain agent runtime directly in the same process.

- Good for local development and quick iteration.
- Uses `OPENAI_API_KEY` from environment/secrets/.env.
- Tool calls happen inside the Streamlit runtime.

### Hosted API Mode

Streamlit sends chat messages to a FastAPI backend (`/qa`) and receives:

- `answer`
- `citations`
- `tool_trace`
- `model`

Hosted mode activates when `ANALYST_API_BASE_URL` is set.

Why this split is useful:

- UI and agent logic are independently deployable.
- Easier to scale and monitor the backend.
- Cleaner boundary for adding auth/rate limits later.

## 3) Financial Analyst Agent (LangChain)

### Objective

Answer company and peer comparison questions with quantitative evidence and clear
source grounding.

### Orchestration Pattern

The graph follows a routed reasoning loop:

1. Router node inspects the latest user message and classifies route: `financial`, `transcript`, `patent`, or `mixed`.
2. Agent node binds a route-specific tool subset.
3. Model decides whether tool calls are needed.
4. Tool node executes requested tools.
5. Control returns to agent for synthesis.
6. Loop ends when no further tool calls are needed.

This enables multi-step evidence gathering instead of one-shot prompting.

### System Prompt Contract

The Financial Analyst prompt requires:

- Direct answer first
- Evidence bullets with concrete values/time periods
- Explicit data gap notes when coverage is missing
- Transcript claims to include source labels

This contract is what keeps responses structured and auditable.

### Available Financial Tools

Current tools include:

- `get_financials`
- `get_ratios`
- `search_transcripts`
- `search_patent_filings`
- `search_news`
- `get_stock_performance`
- `get_company_overview`
- `get_data_coverage`
- `query_financial_database`

These tools pull from curated CSV/JSON snapshots and DuckDB tables.

Route-specific tool binding:

- `financial`: financial metrics, ratios, stock performance, coverage, SQL
- `transcript`: transcripts/news/company context/coverage/SQL
- `patent`: patent search + company context/coverage/SQL
- `mixed`: full tool set

Important retrieval detail:

- `search_transcripts` queries DuckDB (`transcripts` table) directly for speed and consistency.
- Summary CSV coverage is only a fallback note when transcript records are missing.

## 4) Hosted API Service

The backend service exposes agent/data capabilities as HTTP endpoints.

### Endpoints

- `GET /`
- `GET /health`
- `GET /data/coverage`
- `POST /query/financial-sql`
- `POST /search/transcripts`
- `POST /search/patents`
- `POST /qa`

### `/qa` Behavior

Input can be either:

- Full message list (`messages`), or
- Single `question`

Output returns:

- `answer`: final agent response text
- `citations`: transcript citation tokens extracted from final answer
- `tool_trace`: compact list of tool calls with completion preview
- `model`: model identifier used for response

If the backend is missing `OPENAI_API_KEY`, `/qa` returns HTTP 503 with an
explicit configuration message.

If `OPENAI_API_KEY` is a placeholder value (`your-real-key`, `your-key-here`, etc.),
`/qa` also returns HTTP 503 with explicit remediation guidance.

## 5) Evidence and Transparency

Evidence is surfaced at two layers:

### Final Answer Citations

Transcript citations are extracted using the contract format:

`[Transcript: Company Q# YYYY, call date YYYY-MM-DD]`

These are returned as a normalized list in the `/qa` response field `citations`.

### Tool Trace

For each tool call the backend captures:

- Tool name
- Status (`called` or `completed`)
- Tool args (compact)
- Output preview (truncated)

The Streamlit chat panel displays this in an `Evidence` expander under each
assistant response when running in hosted mode.

## 6) Patent Analyst Capability

### Current State

Patent support exists today as searchable summarized metadata, not yet full
retrieval-augmented long-context reasoning over raw patent text.

Available now:

- USPTO extraction pipeline for filing records and full text artifacts
- Ollama-based AI classification and summarization pipeline
- Search endpoint over summarized patent table (`/search/patents`)

Current search fields include:

- Company/ticker filters
- Filing date/year window
- AI-only filter (`ai_only`)
- Text match against title/summary/category/ai_type

### Why this is enough for v1

It answers many strategic questions quickly:

- Which firms appear more active in AI-tagged patent themes?
- What categories dominate each company?
- How filing themes shift over time by company.

## 7) Handling Large Patent Data

As raw patent text grows, sending full filings directly to the model is not
cost-effective or reliable. The practical approach is hierarchical retrieval.

### Stage A: Metadata Narrowing

Filter candidate filings by:

- company/ticker
- years
- category
- ai_type
- keyword constraints

This shrinks the candidate pool before any expensive operation.

### Stage B: Chunk-Level Retrieval (Planned)

For large full-text patent corpora:

1. Chunk abstract/claims/description sections.
2. Build embeddings for chunks.
3. Use hybrid retrieval (keyword + vector similarity).
4. Rerank top candidates and pass only top evidence chunks to the model.

### Stage C: Evidence-First Synthesis

Generate answer from top-ranked chunks and return explicit filing citations.

This keeps context bounded while preserving factual grounding.

## 8) Deployment on Render

The blueprint defines two services:

1. `wheel-street-api` (FastAPI)
2. `wheel-street` (Streamlit)

The frontend uses `ANALYST_API_BASE_URL` as a full host URL (for example,
`https://wheel-street-api.onrender.com`) and routes chat requests through `/qa`.

Benefits:

- Independent restart/scale behavior per service
- Cleaner operational boundary for logs and health checks
- Easier future hardening (auth, rate limits, background jobs)

## 9) Known Constraints

- Snapshot data freshness depends on ETL reruns.
- Patent v1 endpoint searches summaries/metadata, not full semantic chunk index.
- Free hosting tiers may cold-start and increase first-response latency.
- Python 3.14 may produce compatibility warnings in some LangChain components;
	production runtime should prefer Python 3.12/3.13 for stability.

## 10) Learning Checklist

If you want to understand the system by reading code in order, use this path:

1. `src/graph.py`: LangChain loop and agent control flow.
2. `src/tools.py`: evidence tools and DuckDB query guardrails.
3. `api_service/main.py`: hosted endpoint wiring and QA evidence extraction.
4. `app.py`: remote/local mode switch and chat rendering behavior.
5. `data/transform/summarize_uspto_patents_with_ollama.py`: patent AI summary pipeline.
6. `data/load/process_to_duckdb.py`: curated relational store materialization.

## 11) Next Engineering Steps

1. Add API auth for public deployment.
2. Add patent chunk index + hybrid retrieval endpoint.
3. Add structured tabular trace UI (not just bullet previews).
4. Add async background jobs for heavy patent indexing refreshes.
