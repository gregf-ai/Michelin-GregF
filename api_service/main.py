from __future__ import annotations

import os
import re
from functools import lru_cache

import pandas as pd
from fastapi import FastAPI, HTTPException
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from api_service.schemas import (
    GenericTextResponse,
    PatentSearchHit,
    PatentSearchRequest,
    PatentSearchResponse,
    QaRequest,
    QaResponse,
    SqlQueryRequest,
    TextSearchRequest,
    ToolTraceItem,
)
from src.data_loader import COMPANY_NAMES, load_ai_patent_summaries
from src.graph import build_graph
from src.tools import (
    get_data_coverage,
    query_financial_database,
    search_transcripts,
)


app = FastAPI(title="Wheel Street Analyst API", version="0.1.0")

TRANSCRIPT_CITATION_PATTERN = re.compile(r"\[Transcript:\s*[^\]]+\]")


def _to_text(value) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts = []
        for item in value:
            if isinstance(item, dict) and "text" in item:
                parts.append(str(item.get("text", "")))
            else:
                parts.append(str(item))
        return "\n".join([p for p in parts if p])
    return str(value)


def _extract_transcript_citations(answer: str) -> list[str]:
    citations = []
    seen = set()
    for match in TRANSCRIPT_CITATION_PATTERN.findall(answer or ""):
        if match not in seen:
            seen.add(match)
            citations.append(match)
    return citations


def _collect_tool_trace(messages: list) -> list[ToolTraceItem]:
    traces: list[ToolTraceItem] = []
    pending: dict[str, int] = {}

    for msg in messages:
        if isinstance(msg, AIMessage) and msg.tool_calls:
            for call in msg.tool_calls:
                item = ToolTraceItem(
                    tool=str(call.get("name", "tool")),
                    status="called",
                    args=call.get("args") or {},
                    output_preview="",
                )
                traces.append(item)
                call_id = call.get("id")
                if call_id:
                    pending[str(call_id)] = len(traces) - 1

        elif isinstance(msg, ToolMessage):
            preview = _to_text(msg.content)[:500]
            tool_call_id = getattr(msg, "tool_call_id", None)
            if tool_call_id and str(tool_call_id) in pending:
                idx = pending[str(tool_call_id)]
                traces[idx].status = "completed"
                traces[idx].output_preview = preview
            else:
                traces.append(
                    ToolTraceItem(
                        tool=str(getattr(msg, "name", "tool")),
                        status="completed",
                        args={},
                        output_preview=preview,
                    )
                )

    return traces


def _resolve_company_filter(company: str) -> tuple[str | None, str]:
    if (company or "all").lower() == "all":
        return None, "all"

    upper = company.upper().strip()
    if upper in COMPANY_NAMES:
        return upper, COMPANY_NAMES[upper]

    for ticker, name in COMPANY_NAMES.items():
        if name.lower() == company.lower().strip():
            return ticker, name

    return None, ""


@lru_cache(maxsize=1)
def _agent_graph():
    model_name = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    return build_graph(model_name=model_name)


@lru_cache(maxsize=1)
def _patent_df() -> pd.DataFrame:
    df = load_ai_patent_summaries().copy()
    if df.empty:
        return df

    if "filing_date" in df.columns:
        df["filing_date"] = pd.to_datetime(df["filing_date"], errors="coerce")
    else:
        df["filing_date"] = pd.NaT

    df["_search_text"] = (
        df.get("invention_title", "").fillna("").astype(str)
        + " "
        + df.get("short_summary", "").fillna("").astype(str)
        + " "
        + df.get("patent_category", "").fillna("").astype(str)
        + " "
        + df.get("ai_type", "").fillna("").astype(str)
    ).str.lower()

    return df


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "api": "wheel-street-analyst",
        "model": os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
    }


@app.get("/")
def root() -> dict:
    return {
        "service": "wheel-street-analyst-api",
        "status": "ok",
        "health": "/health",
        "endpoints": [
            "/data/coverage",
            "/query/financial-sql",
            "/search/transcripts",
            "/search/patents",
            "/qa",
        ],
    }


@app.get("/data/coverage", response_model=GenericTextResponse)
def data_coverage() -> GenericTextResponse:
    return GenericTextResponse(result=get_data_coverage.invoke({}))


@app.post("/query/financial-sql", response_model=GenericTextResponse)
def financial_sql(req: SqlQueryRequest) -> GenericTextResponse:
    result = query_financial_database.invoke({"sql_query": req.sql_query})
    return GenericTextResponse(result=result)


@app.post("/search/transcripts", response_model=GenericTextResponse)
def transcripts(req: TextSearchRequest) -> GenericTextResponse:
    result = search_transcripts.invoke(
        {
            "query": req.query,
            "company": req.company,
            "years": req.years,
            "max_results": req.max_results,
        }
    )
    return GenericTextResponse(result=result)


@app.post("/search/patents", response_model=PatentSearchResponse)
def patents(req: PatentSearchRequest) -> PatentSearchResponse:
    df = _patent_df()
    if df.empty:
        return PatentSearchResponse(total_matches=0, returned=0, hits=[])

    filtered = df
    ticker, company_name = _resolve_company_filter(req.company)
    if req.company.lower() != "all" and not ticker:
        raise HTTPException(status_code=400, detail=f"Unknown company: {req.company}")

    if ticker:
        filtered = filtered[filtered["ticker"] == ticker]
    elif company_name and "company" in filtered.columns:
        filtered = filtered[filtered["company"] == company_name]

    if req.years > 0:
        cutoff_year = pd.Timestamp.utcnow().year - req.years + 1
        filtered = filtered[filtered["filing_date"].dt.year >= cutoff_year]

    if req.ai_only:
        filtered = filtered[filtered["ai_driven"] == True]

    terms = [t.strip().lower() for t in req.query.split() if t.strip()]
    if terms:
        mask = pd.Series(True, index=filtered.index)
        for term in terms:
            mask = mask & filtered["_search_text"].str.contains(term, regex=False)
        filtered = filtered[mask]

    filtered = filtered.sort_values(["filing_date", "confidence"], ascending=[False, False])
    total = len(filtered)
    trimmed = filtered.head(req.max_results)

    hits: list[PatentSearchHit] = []
    for _, row in trimmed.iterrows():
        filing_date = ""
        if pd.notna(row.get("filing_date")):
            filing_date = str(row.get("filing_date"))[:10]

        hits.append(
            PatentSearchHit(
                ticker=str(row.get("ticker", "")),
                company=str(row.get("company", "")),
                filing_date=filing_date,
                application_number=str(row.get("application_number", "")),
                invention_title=str(row.get("invention_title", "")),
                ai_driven=bool(row.get("ai_driven", False)),
                ai_type=str(row.get("ai_type", "none")),
                patent_category=str(row.get("patent_category", "other")),
                confidence=float(row.get("confidence", 0.0) or 0.0),
                short_summary=str(row.get("short_summary", "")),
            )
        )

    return PatentSearchResponse(total_matches=total, returned=len(hits), hits=hits)


@app.post("/qa", response_model=QaResponse)
def qa(req: QaRequest) -> QaResponse:
    if not os.environ.get("OPENAI_API_KEY"):
        raise HTTPException(status_code=503, detail="OPENAI_API_KEY is not configured on the API service.")

    messages = []

    if req.messages:
        for msg in req.messages:
            if msg.role == "user":
                messages.append(HumanMessage(content=msg.content))
            elif msg.role == "assistant":
                messages.append(AIMessage(content=msg.content))
    elif req.question:
        messages.append(HumanMessage(content=req.question))
    else:
        raise HTTPException(status_code=400, detail="Provide either question or messages.")

    try:
        result = _agent_graph().invoke({"messages": messages})
        output_messages = result.get("messages", [])
        answer = _to_text(output_messages[-1].content) if output_messages else ""
        citations = _extract_transcript_citations(answer)
        tool_trace = _collect_tool_trace(output_messages)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Agent execution failed: {exc}") from exc

    return QaResponse(
        answer=answer,
        model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        citations=citations,
        tool_trace=tool_trace,
    )
