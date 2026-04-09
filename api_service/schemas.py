from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class MessageIn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1)


class QaRequest(BaseModel):
    question: str | None = Field(default=None)
    messages: list[MessageIn] = Field(default_factory=list)


class ToolTraceItem(BaseModel):
    tool: str
    status: str
    args: dict = Field(default_factory=dict)
    output_preview: str = ""


class QaResponse(BaseModel):
    answer: str
    model: str
    citations: list[str] = Field(default_factory=list)
    tool_trace: list[ToolTraceItem] = Field(default_factory=list)


class SqlQueryRequest(BaseModel):
    sql_query: str = Field(min_length=1)


class TextSearchRequest(BaseModel):
    query: str = Field(min_length=1)
    company: str = "all"
    years: int = 0
    max_results: int = 20


class PatentSearchRequest(BaseModel):
    query: str = Field(min_length=1)
    company: str = "all"
    years: int = 0
    max_results: int = 20
    ai_only: bool = False


class GenericTextResponse(BaseModel):
    result: str


class PatentSearchHit(BaseModel):
    ticker: str
    company: str
    filing_date: str
    application_number: str
    invention_title: str
    ai_driven: bool
    ai_type: str
    patent_category: str
    confidence: float
    short_summary: str


class PatentSearchResponse(BaseModel):
    total_matches: int
    returned: int
    hits: list[PatentSearchHit]
