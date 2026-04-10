# Validation

## Data Validation
- Confirm expected files exist per company and endpoint.
- Verify key columns and numeric coercion in load stage.
- Spot-check outliers and missingness by metric/company/year.

## Chart Validation
- Verify ranking order against source values.
- Verify toggle behavior (2025 vs 10-year median).
- Verify selected-bar drilldowns show expected underlying series.

## Agent Validation
- Run benchmark prompts and confirm numeric grounding.
- Check missing-data handling language is explicit.
- Validate multi-company comparisons return peer-specific values.
- Validate routing behavior with route-specific prompts:
	- Financial prompt -> financial tools
	- Transcript prompt -> transcript tools
	- Patent prompt -> patent tools

## API Validation
- `GET /` returns endpoint index payload.
- `GET /health` returns status/model.
- `GET /data/coverage` returns coverage text.
- `POST /qa` returns `answer`, `citations`, and `tool_trace`.
- Confirm `/qa` returns HTTP 503 when `OPENAI_API_KEY` is missing/placeholder.

## Smoke Test
1. Start API and run `scripts/local_api_smoke.ps1`.
2. Start `streamlit run app.py`.
3. Open dashboard tabs and verify charts load.
4. Ask 3 benchmark analyst questions, including a transcript-specific prompt.
5. Confirm evidence expander shows tool trace and citations in hosted mode.
6. Confirm no runtime exceptions in terminal.
