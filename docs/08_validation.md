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

## Smoke Test
1. `streamlit run app.py`
2. Open dashboard tabs and verify charts load.
3. Ask 3 benchmark analyst questions.
4. Confirm no runtime exceptions in terminal.
