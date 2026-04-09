# Reproducibility

## Local Setup
1. `pip install -r requirements.txt`
2. Set `OPENAI_API_KEY`
3. `streamlit run app.py`

## Optional Data Refresh
1. Set `ROIC_API_KEY`
2. Run `python data/extract/download.py`
3. Run `python data/load/process_to_duckdb.py`

## Docker
1. `docker build -t wheel-street .`
2. `docker run -p 8501:8501 -e OPENAI_API_KEY=<key> wheel-street`

## Render
1. Connect repo as Docker service.
2. Set `OPENAI_API_KEY` env var.
3. Deploy from main branch.

## Deterministic Review Notes
- Uses committed local snapshots for stable interview demos.
- Curated analytics outputs are versioned under `data/processed/curated`.
