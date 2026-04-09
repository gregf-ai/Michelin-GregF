# Agents

## Financial Analyst Agent

### Objective
Answer company and peer comparison questions with grounded quantitative evidence.

### Toolchain
- Orchestrator: LangGraph
- Tools: financial retrieval, ratios, transcripts/news search, stock performance, company overview, DuckDB query tool
- Data backends: local JSON + DuckDB

### Workflow
1. Parse intent and identify evidence needed.
2. Call one or more tools.
3. Iterate when evidence is incomplete.
4. Return concise answer with numeric support and caveats.

### Response Expectations
- Direct answer first.
- Evidence bullets with values and periods.
- Explicit note on data gaps and assumptions.

## Patent Analyst Agent

### Objective
Support innovation and patent-position analysis from USPTO-derived data.

### Current State
- ETL and summarization paths exist for patent datasets.
- Interview narrative includes patent analytics scope and extension plan.
- Full standalone patent chat workflow is a next-step enhancement.

### Planned Workflow
1. Retrieve patent dataset slices by company/theme.
2. Summarize technology areas and trend intensity.
3. Compare innovation focus across peers.
4. Return evidence-backed qualitative insights.
