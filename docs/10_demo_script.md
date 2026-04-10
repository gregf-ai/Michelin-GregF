# Demo Script (5 Minutes)

## 0:00 - 0:30 | Problem Framing
- Objective: evaluate whether Michelin has a durable competitive moat versus peers.
- Method: combine financial trend/ranking analytics with AI-assisted evidence retrieval.

## 0:30 - 2:30 | Financial Dashboard Walkthrough
- Show thesis, methodology, and conclusion block.
- Open each key tab (Margin, ROIC, Growth metrics).
- Explain 10-year median vs 2025 toggle.
- Click a bar to show company-specific drilldown behavior.

## 2:30 - 4:00 | Agent Walkthrough
- Ask prepared prompts:
  - Why does Michelin maintain higher margins than competitors?
  - Summarize Michelin's 2025 earnings transcript.
  - Which peer has strongest shareholder return profile?
  - What evidence supports Michelin's weakest growth area?
- Highlight tool-grounded, numeric responses.
- Open Evidence expander to show citations and tool trace.

## 4:00 - 5:00 | Architecture and Tradeoffs
- Explain snapshot-based reliability vs data freshness tradeoff.
- Explain LangChain router flow (`financial|transcript|patent|mixed`) and route-specific tools.
- Explain hosted split: Streamlit UI -> FastAPI `/qa` endpoint.
- Close with roadmap: deeper patent UX and automated ETL manifests.
