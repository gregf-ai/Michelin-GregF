"""Summarize news and earnings transcripts with Ollama and save to data/processed.

Usage examples:
  c:/Michelin-GregF/.venv/Scripts/python.exe data/summarize_with_ollama.py
  c:/Michelin-GregF/.venv/Scripts/python.exe data/summarize_with_ollama.py --model qwen2.5:14b-instruct-q4_K_M
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import pandas as pd
import requests

RAW_DIR = Path(__file__).resolve().parent / "raw"
OUT_DIR = Path(__file__).resolve().parent / "processed"
OLLAMA_URL = "http://localhost:11434/api/generate"

TICKER_TO_COMPANY = {
    "MGDDY": "Michelin",
    "GT": "Goodyear",
    "BRDCY": "Bridgestone",
    "CTTAY": "Continental",
    "PLLIF": "Pirelli",
    "SSUMY": "Sumitomo",
}


def call_ollama(prompt: str, model: str, temperature: float = 0.2) -> str:
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": temperature,
        },
    }
    response = requests.post(OLLAMA_URL, json=payload, timeout=240)
    response.raise_for_status()
    data = response.json()
    return data.get("response", "").strip()


def enforce_headings(summary_text: str, model: str, required_headings: list[str]) -> str:
    """Force output into a strict markdown section template."""
    if all(h in summary_text for h in required_headings):
        return summary_text

    headings_block = "\n".join(required_headings)
    prompt = (
        "Reformat the following analyst notes into markdown using these exact headings, in this exact order.\n"
        "If a section has no evidence, write 'Not explicitly disclosed in provided material.'\n"
        "Do not add or rename headings.\n\n"
        f"Required headings:\n{headings_block}\n\n"
        f"Notes to format:\n{summary_text}"
    )
    return call_ollama(prompt, model=model, temperature=0)


def validate_summary_quality(summary_text: str, required_headings: list[str]) -> dict[str, Any]:
    """Run lightweight validation checks without blocking pipeline output."""
    line_count = len([line for line in summary_text.splitlines() if line.strip()])
    fallback_hits = len(
        re.findall(
            r"Not explicitly disclosed in provided material|Not disclosed in provided articles|Not discussed in call",
            summary_text,
            flags=re.IGNORECASE,
        )
    )
    numeric_hits = len(
        re.findall(r"(?:[$€]|\b)\d+(?:,\d{3})*(?:\.\d+)?(?:\s*(?:%|bps|B|M|K|x))?", summary_text)
    )
    return {
        "missing_headings": [h for h in required_headings if h not in summary_text],
        "line_count": line_count,
        "fallback_ratio": (fallback_hits / max(line_count, 1)),
        "numeric_hits": numeric_hits,
    }


def audit_summary_df(df: pd.DataFrame, required_headings: list[str], label: str) -> None:
    if df.empty:
        print(f"{label}: no rows to audit")
        return

    warnings = 0
    for _, row in df.iterrows():
        summary = row.get("summary", "")
        if not isinstance(summary, str):
            continue
        check = validate_summary_quality(summary, required_headings)
        who = row.get("ticker", "?")
        if check["missing_headings"]:
            warnings += 1
            print(f"WARN [{label}] {who}: missing headings -> {check['missing_headings']}")
        if check["numeric_hits"] < 2:
            warnings += 1
            print(f"WARN [{label}] {who}: sparse numeric evidence (hits={check['numeric_hits']})")
        if check["fallback_ratio"] > 0.30:
            warnings += 1
            print(f"WARN [{label}] {who}: high fallback density ({check['fallback_ratio']:.1%})")

    if warnings == 0:
        print(f"{label}: quality checks passed")


def read_json(path: Path) -> Any:
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def summarize_news_for_ticker(ticker: str, model: str, max_articles: int) -> dict[str, Any]:
    company = TICKER_TO_COMPANY[ticker]
    news_path = RAW_DIR / "news" / f"{ticker}.json"
    articles = read_json(news_path) or []

    if not isinstance(articles, list):
        articles = []

    articles = sorted(articles, key=lambda a: a.get("published_date", ""), reverse=True)
    selected = articles[:max_articles]

    if not selected:
        return {
            "ticker": ticker,
            "company": company,
            "article_count": 0,
            "date_start": "",
            "date_end": "",
            "summary": "No articles available.",
            "model": model,
        }

    lines = []
    for i, a in enumerate(selected, start=1):
        title = (a.get("title") or "").strip().replace("\n", " ")
        date = (a.get("published_date") or "")[:10]
        text = (a.get("article_text") or "").strip().replace("\n", " ")
        snippet = text[:900]
        lines.append(f"{i}. [{date}] {title}\n{snippet}")

    prompt = (
        f"You are a senior equity research analyst. Summarize recent news for {company} ({ticker}).\n"
        "Using only the provided items, produce Markdown with these exact headings:\n"
        "## Executive Summary\n"
        "- 5 bullets with explicit source dates in each bullet\n"
        "## Financial Headwinds & Tailwinds\n"
        "- Explain why performance likely improved or deteriorated by period where available\n"
        "- Include concrete drivers (volume/price/mix/cost/FX/tariffs/demand) and cite evidence\n"
        "- If a requested driver is absent, write: Not explicitly disclosed in provided material.\n"
        "## Major Innovations\n"
        "- Product/technology/AI innovations explicitly mentioned with dates\n"
        "## Major Initiatives\n"
        "- Strategic programs, restructuring, partnerships, market expansion\n"
        "- Include workforce signals if present (headcount, layoffs, hiring, engagement, leadership)\n"
        "- If workforce signals are absent, state that explicitly\n"
        "## Large Investments\n"
        "- Capex, M&A, divestitures, plant expansion, R&D spend, digital investments\n"
        "- Include numeric scale and timing when available\n"
        "## Risks and Opportunities\n"
        "- Balanced and concise, grounded only in provided text\n"
        "## Investor Takeaway\n"
        "- 2 sentences\n"
        "Be concise, factual, and avoid speculation beyond provided text.\n"
        "Do not use generic filler; every claim should be tied to a provided item.\n\n"
        "News items:\n"
        + "\n\n".join(lines)
    )

    summary = call_ollama(prompt, model=model)
    summary = enforce_headings(
        summary,
        model=model,
        required_headings=[
            "## Executive Summary",
            "## Financial Headwinds & Tailwinds",
            "## Major Innovations",
            "## Major Initiatives",
            "## Large Investments",
            "## Risks and Opportunities",
            "## Investor Takeaway",
        ],
    )

    dates = [((a.get("published_date") or "")[:10]) for a in selected if a.get("published_date")]
    return {
        "ticker": ticker,
        "company": company,
        "article_count": len(selected),
        "date_start": min(dates) if dates else "",
        "date_end": max(dates) if dates else "",
        "summary": summary,
        "model": model,
    }


def summarize_transcripts_for_ticker(ticker: str, model: str, max_transcripts: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    company = TICKER_TO_COMPANY[ticker]
    transcript_path = RAW_DIR / "transcripts" / f"{ticker}.json"
    transcripts = read_json(transcript_path) or []

    if not isinstance(transcripts, list):
        transcripts = []

    transcripts = sorted(
        transcripts,
        key=lambda t: (int(t.get("year") or 0), int(t.get("quarter") or 0)),
        reverse=True,
    )
    selected = transcripts[:max_transcripts]

    per_transcript_rows: list[dict[str, Any]] = []

    if not selected:
        company_row = {
            "ticker": ticker,
            "company": company,
            "transcript_count": 0,
            "latest_period": "",
            "summary": "No transcripts available.",
            "model": model,
        }
        return per_transcript_rows, company_row

    for t in selected:
        year = t.get("year", "?")
        quarter = t.get("quarter", "?")
        date = (t.get("date") or "")[:10]
        content = (t.get("content") or "")
        excerpt = content[:12000]

        prompt = (
            f"Summarize this earnings call transcript for {company} ({ticker}), Q{quarter} {year}.\n"
            "Return Markdown with these exact headings:\n"
            "## Executive Summary\n"
            "- 4 key business highlights\n"
            "## Financial Headwinds & Tailwinds\n"
            "- Explain why the quarter went well or poorly based on management commentary\n"
            "- Include concrete drivers (volume/price/mix/cost/FX/demand) and timing where available\n"
            "## Major Innovations\n"
            "- AI, software, manufacturing, and product innovation mentions\n"
            "## Major Initiatives\n"
            "- Management strategic priorities and operating programs\n"
            "- Include workforce details if discussed (headcount, hiring/layoffs, engagement, org changes)\n"
            "## Large Investments\n"
            "- Capex, acquisitions, divestitures, restructuring, footprint expansion references\n"
            "## Financial Callouts\n"
            "- 3 numeric callouts with explicit values and context\n"
            "## Tone and Outlook\n"
            "- Management confidence/caution and forward view\n"
            "If a topic is not mentioned, write: Not explicitly disclosed in provided material.\n"
            "Be factual and concise.\n\n"
            f"Transcript excerpt:\n{excerpt}"
        )

        summary = call_ollama(prompt, model=model)
        summary = enforce_headings(
            summary,
            model=model,
            required_headings=[
                "## Executive Summary",
                "## Financial Headwinds & Tailwinds",
                "## Major Innovations",
                "## Major Initiatives",
                "## Large Investments",
                "## Financial Callouts",
                "## Tone and Outlook",
            ],
        )
        per_transcript_rows.append(
            {
                "ticker": ticker,
                "company": company,
                "year": year,
                "quarter": quarter,
                "date": date,
                "summary": summary,
                "model": model,
            }
        )

    # Build a company-level meta-summary from per-transcript summaries
    stitched = "\n\n".join(
        [
            f"Q{r['quarter']} {r['year']}:\n{r['summary'][:1400]}"
            for r in per_transcript_rows
        ]
    )

    meta_prompt = (
        f"You are an industry analyst. Synthesize these earnings call summaries for {company} ({ticker}).\n"
        "Return Markdown with these exact headings:\n"
        "## Trend Summary Across Periods\n"
        "- 5 bullets\n"
        "## What Changed Most Recently\n"
        "- Recent vs prior periods with explicit what-improved/what-worsened details\n"
        "## Financial Headwinds & Tailwinds\n"
        "- Consolidated cross-period assessment with concrete drivers\n"
        "## Major Innovations\n"
        "- Most meaningful innovation trend(s)\n"
        "## Major Initiatives\n"
        "- Strategic priorities repeated by management\n"
        "- Include recurring workforce and restructuring themes when available\n"
        "## Large Investments\n"
        "- Largest recurring or announced investments (including M&A/divestitures/capex)\n"
        "## Top 3 Watch Items\n"
        "- For next earnings call\n"
        "Stay grounded in provided summaries only.\n\n"
        f"Transcript summaries:\n{stitched}"
    )

    company_summary = call_ollama(meta_prompt, model=model)
    company_summary = enforce_headings(
        company_summary,
        model=model,
        required_headings=[
            "## Trend Summary Across Periods",
            "## What Changed Most Recently",
            "## Financial Headwinds & Tailwinds",
            "## Major Innovations",
            "## Major Initiatives",
            "## Large Investments",
            "## Top 3 Watch Items",
        ],
    )
    latest = per_transcript_rows[0]
    company_row = {
        "ticker": ticker,
        "company": company,
        "transcript_count": len(per_transcript_rows),
        "latest_period": f"Q{latest['quarter']} {latest['year']}",
        "summary": company_summary,
        "model": model,
    }

    return per_transcript_rows, company_row


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize news and transcripts with Ollama")
    parser.add_argument("--model", default="qwen2.5:14b-instruct-q4_K_M", help="Ollama model name")
    parser.add_argument("--max-news", type=int, default=120, help="Max news articles per ticker")
    parser.add_argument("--max-transcripts", type=int, default=12, help="Max transcripts per ticker")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # quick connectivity check
    try:
        _ = call_ollama("Reply with: OK", model=args.model, temperature=0)
    except Exception as exc:
        raise RuntimeError(
            "Unable to call Ollama. Ensure Ollama is running and model is available. "
            f"Model: {args.model}. Error: {exc}"
        ) from exc

    news_rows = []
    transcript_rows = []
    transcript_company_rows = []

    for ticker in TICKER_TO_COMPANY:
        print(f"Summarizing news for {ticker}...")
        news_rows.append(summarize_news_for_ticker(ticker, model=args.model, max_articles=args.max_news))

        print(f"Summarizing transcripts for {ticker}...")
        per_rows, company_row = summarize_transcripts_for_ticker(
            ticker,
            model=args.model,
            max_transcripts=args.max_transcripts,
        )
        transcript_rows.extend(per_rows)
        transcript_company_rows.append(company_row)

    news_df = pd.DataFrame(news_rows)
    t_df = pd.DataFrame(transcript_rows)
    tc_df = pd.DataFrame(transcript_company_rows)

    news_path = OUT_DIR / "news_summaries_ollama.csv"
    transcript_path = OUT_DIR / "transcript_summaries_ollama.csv"
    transcript_company_path = OUT_DIR / "transcript_company_summaries_ollama.csv"

    news_df.to_csv(news_path, index=False)
    t_df.to_csv(transcript_path, index=False)
    tc_df.to_csv(transcript_company_path, index=False)

    # Lightweight validation-only checks (warnings, no hard fail).
    audit_summary_df(
        news_df,
        [
            "## Executive Summary",
            "## Financial Headwinds & Tailwinds",
            "## Major Innovations",
            "## Major Initiatives",
            "## Large Investments",
            "## Risks and Opportunities",
            "## Investor Takeaway",
        ],
        "news",
    )
    audit_summary_df(
        t_df,
        [
            "## Executive Summary",
            "## Financial Headwinds & Tailwinds",
            "## Major Innovations",
            "## Major Initiatives",
            "## Large Investments",
            "## Financial Callouts",
            "## Tone and Outlook",
        ],
        "transcript",
    )
    audit_summary_df(
        tc_df,
        [
            "## Trend Summary Across Periods",
            "## What Changed Most Recently",
            "## Financial Headwinds & Tailwinds",
            "## Major Innovations",
            "## Major Initiatives",
            "## Large Investments",
            "## Top 3 Watch Items",
        ],
        "transcript-company",
    )

    print(f"Wrote {news_path} ({len(news_df)} rows)")
    print(f"Wrote {transcript_path} ({len(t_df)} rows)")
    print(f"Wrote {transcript_company_path} ({len(tc_df)} rows)")
    print("Done.")


if __name__ == "__main__":
    main()
