# Tech Stack

## Application Layer
- Python 3.x
- Streamlit for interactive UI and rapid iteration
- Plotly for analytical charting and selection interactions

## AI Layer
- LangChain for tool interface and model integration
- LangChain for router-based orchestration (`financial|transcript|patent|mixed`)
- OpenAI Chat models for analyst responses

## Data Layer
- ROIC.ai API and USPTO data ingestion
- Local JSON snapshot storage for deterministic runs
- DuckDB for queryable analytical store
- Pandas for transformations and metric computation

## Deployment Layer
- Dockerized runtime
- Render blueprint with two services:
	- `wheel-street` (Streamlit frontend)
	- `wheel-street-api` (FastAPI backend)

## Why This Stack
- Fast to build, easy to demo, and clear tradeoffs for interview discussion.
- Strong signal on practical AI-agent orchestration with grounded, route-aware tools.
