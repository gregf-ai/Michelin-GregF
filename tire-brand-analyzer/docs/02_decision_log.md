# Decision Log

## 2026-04-08 — UI Stack: Streamlit Multipage
- Decision: Use Streamlit for end-to-end UI.
- Why: Fastest path to a polished, interactive demo in two days.
- Tradeoff: Less custom frontend flexibility than React.

## 2026-04-08 — Agent Framework: LangGraph + LangChain
- Decision: Implement tool-calling agent with LangGraph loop.
- Why: Strong interview signal for agentic workflow and orchestration.
- Tradeoff: Slightly more complexity than a single chain.

## 2026-04-08 — Deployment: Docker on Render
- Decision: Deploy as Docker web service on Render free tier.
- Why: Straightforward GitHub integration and easy reproducibility.
- Tradeoff: Free tier cold starts.

## 2026-04-08 — Data Strategy: Pre-download and Commit Snapshot
- Decision: Download data into JSON and serve from local files.
- Why: Demo stability, deterministic outputs, no runtime dependency on ROIC key.
- Tradeoff: Data can become stale.

## 2026-04-08 — Currency Policy: Normalize Financial Values to USD
- Decision: Convert EUR and JPY monetary fields to USD using annual average FX tables.
- Why: Enable apples-to-apples cross-company comparison.
- Tradeoff: Approximate FX conversion rather than transaction-date precision.

## 2026-04-08 — Transcript and News Breadth
- Decision: Pull transcripts from 2021+ and paginate news for larger coverage.
- Why: Better evidence base for qualitative AI questions.
- Tradeoff: Larger local dataset and slightly longer build step.
