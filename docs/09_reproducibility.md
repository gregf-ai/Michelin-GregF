# Reproducibility

## Local Setup
1. `pip install -r requirements.txt`
2. Configure `.env` (or environment vars):
	- `OPENAI_API_KEY`
	- `ROIC_API_KEY` (for refresh jobs)
	- `ANALYST_API_BASE_URL` (for hosted-mode UI; local example below)

## Local Run (Hosted-Mode UI + API)
1. Start API: `python -m uvicorn api_service.main:app --host 127.0.0.1 --port 8000`
2. Set `ANALYST_API_BASE_URL=http://127.0.0.1:8000`
3. Start UI: `streamlit run app.py`

## Local Run (In-Process Agent Mode)
1. Unset `ANALYST_API_BASE_URL`
2. `streamlit run app.py`

## Optional Data Refresh
1. Full refresh:
	- `python data/extract/download.py`
	- `python data/load/process_to_duckdb.py`
2. Transcript-only refresh:
	- `python data/extract/download.py --types transcripts`
	- `python data/transform/parse_manual_transcripts.py`
	- `python data/load/process_to_duckdb.py --sync-transcripts-only`

## Docker
1. `docker build -t wheel-street .`
2. `docker run -p 8501:8501 -e OPENAI_API_KEY=<key> wheel-street`

## Render
1. Deploy from `render.yaml` as a two-service blueprint.
2. API service (`wheel-street-api`) env:
	- `OPENAI_API_KEY`
3. Frontend service (`wheel-street`) env:
	- `ANALYST_API_BASE_URL=https://wheel-street-api.onrender.com`

## Deterministic Review Notes
- Uses committed local snapshots for stable interview demos.
- Curated analytics outputs are versioned under `data/processed/curated`.
