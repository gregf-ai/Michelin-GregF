# Limitations and Risks

## Data Risks
- Snapshot-based data can become stale.
- Coverage differs by source, ticker, and endpoint.
- Some transcript/news/patent availability is uneven.

## Analytical Risks
- Outliers can distort growth metrics if not handled explicitly.
- Currency normalization and aggregation choices affect comparability.
- Median-based ranking can mask recent step-changes.

## Agent Risks
- LLM quality depends on route classification and tool selection.
- Hallucination risk is mitigated but not eliminated.
- Heuristic router can misclassify ambiguous prompts into suboptimal tool subsets.
- SQL tool misuse could produce misleading summaries without validation.

## Operational Risks
- Render free-tier cold starts affect demo responsiveness.
- API/provider changes can break future refresh runs.
