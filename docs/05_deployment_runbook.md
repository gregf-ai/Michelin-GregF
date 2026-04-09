# Deployment Runbook

## Local Run (Python)
1. Install dependencies:
   - python -m pip install -r requirements.txt
2. Set environment variable:
   - OPENAI_API_KEY=<your key>
3. Launch:
   - streamlit run app.py

## Local Run (Docker)
1. Build:
   - docker build -t tire-brand-analyzer .
2. Run:
   - docker run -p 8501:8501 -e OPENAI_API_KEY=<your key> tire-brand-analyzer
3. Open:
   - http://localhost:8501

## Render Deployment (Docker)
1. Push repository to GitHub.
2. In Render: New Web Service -> Connect repo.
3. Runtime: Docker from the repo root (render.yaml is included at the repo root).
4. Set env var:
   - OPENAI_API_KEY
5. Deploy and verify health.

## Smoke Test Checklist
- Home page loads and summary cards render.
- Dashboard filters work and charts render.
- Profiles page shows news and transcripts where available.
- AI Analyst answers at least 3 benchmark prompts with numeric evidence.

## Known Runtime Notes
- Free tier may cold start after idle.
- Ensure OPENAI_API_KEY is configured in Render environment settings.
