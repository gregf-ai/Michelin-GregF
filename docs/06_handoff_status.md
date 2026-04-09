# Handoff Status

## Current State
- Core app implemented (home, dashboard, profiles, AI analyst).
- Data snapshot expanded to 15 years for core financials.
- Currency normalization to USD added in loader stage.
- News pagination and multi-transcript retrieval added.
- Docker and Render configuration present.
- Data folder cleanup completed for logs/backups.
- ETL scripts now live only in `data/extract`, `data/transform`, and `data/load`.
- Duplicate root-level outputs removed from `data/processed` (curated/analytics are canonical).

## Open Risks
- FX conversion uses annual averages, not date-specific rates.
- Transcript/news coverage is dependent on source availability.
- LLM output quality depends on prompt quality and tool routing.
- Run manifests are documented but not yet emitted automatically by ETL scripts.

## Next 3 Tasks
1. Add a run manifest per ETL job (`run_id`, started_at, input snapshot, output artifact paths).
2. Add a lightweight app startup smoke test to CI (or a local scripted check).
3. Run benchmark AI queries and capture screenshots for submission.

## Demo-Day Checklist
- Warm up Render instance 5-10 minutes before interview.
- Keep 3 prepared prompts for AI analyst.
- Keep one example of missing-data handling (for transparency).
