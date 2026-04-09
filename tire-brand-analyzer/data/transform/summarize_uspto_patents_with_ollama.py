"""Summarize USPTO ODP patent full text with Ollama and materialize AI patent analytics.

This script reads `data/raw/uspto_odp/<TICKER>/filings_with_text.jsonl`,
classifies patents into AI-related categories, and writes:
- data/processed/analytics/patent_ai_summaries_ollama.csv
- data/processed/analytics/patent_ai_company_stats.csv
- data/processed/analytics/patent_ai_summaries_ollama.jsonl (checkpoint output)
- data/processed/analytics/patent_ai_analyst.duckdb

Default behavior analyzes likely AI candidates only for speed and treats
non-candidates as non-AI in aggregate company totals.

Usage examples:
    c:/Michelin-GregF/.venv/Scripts/python.exe data/transform/summarize_uspto_patents_with_ollama.py
    c:/Michelin-GregF/.venv/Scripts/python.exe data/transform/summarize_uspto_patents_with_ollama.py --tickers MGDDY,GT,BRDCY,CTTAY
    c:/Michelin-GregF/.venv/Scripts/python.exe data/transform/summarize_uspto_patents_with_ollama.py --analyze-all --max-per-ticker 100
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd
import requests

DATA_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = DATA_ROOT / "raw" / "uspto_odp"
OUT_DIR = DATA_ROOT / "processed" / "analytics"
OLLAMA_URL = "http://localhost:11434/api/generate"

TICKER_TO_COMPANY = {
    "MGDDY": "Michelin",
    "GT": "Goodyear",
    "BRDCY": "Bridgestone",
    "CTTAY": "Continental",
    "PLLIF": "Pirelli",
    "SSUMY": "Sumitomo",
}

AI_KEYWORD_PATTERN = re.compile(
    r"machine learning|deep learning|neural network|artificial intelligence|"
    r"generative ai|large language model|\bllm\b|computer vision|"
    r"natural language processing|\bnlp\b|reinforcement learning|"
    r"predictive model|autonomous driving|image recognition",
    re.IGNORECASE,
)

VALID_AI_TYPES = {
    "none",
    "machine_learning",
    "deep_learning",
    "computer_vision",
    "nlp",
    "generative_ai",
    "optimization_ai",
    "autonomy_robotics",
    "other_ai",
}

VALID_PATENT_CATEGORIES = {
    "adas_and_safety",
    "vehicle_control_systems",
    "manufacturing_process",
    "materials_and_chemistry",
    "tire_design_and_performance",
    "telematics_and_sensing",
    "enterprise_software_and_it",
    "sustainability_and_energy",
    "other",
}


def call_ollama(prompt: str, model: str, temperature: float = 0.1) -> str:
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": temperature,
        },
    }
    response = requests.post(OLLAMA_URL, json=payload, timeout=300)
    response.raise_for_status()
    return response.json().get("response", "").strip()


def parse_json_object(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)

    try:
        obj = json.loads(text)
        return obj if isinstance(obj, dict) else {}
    except json.JSONDecodeError:
        pass

    # Salvage first JSON object from mixed output.
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        try:
            obj = json.loads(text[start : end + 1])
            return obj if isinstance(obj, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def normalize_ai_type(value: Any) -> str:
    candidate = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "ml": "machine_learning",
        "ai_ml": "machine_learning",
        "gen_ai": "generative_ai",
        "generative": "generative_ai",
        "computer_vision_ai": "computer_vision",
        "robotics": "autonomy_robotics",
    }
    candidate = aliases.get(candidate, candidate)
    return candidate if candidate in VALID_AI_TYPES else "other_ai"


def normalize_category(value: Any) -> str:
    candidate = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "adas": "adas_and_safety",
        "sensors": "telematics_and_sensing",
        "materials": "materials_and_chemistry",
        "tire_design": "tire_design_and_performance",
        "enterprise_it": "enterprise_software_and_it",
        "energy": "sustainability_and_energy",
    }
    candidate = aliases.get(candidate, candidate)
    return candidate if candidate in VALID_PATENT_CATEGORIES else "other"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                rows.append(obj)
    return rows


def build_text_payload(record: dict[str, Any], max_chars: int) -> str:
    title = str(record.get("invention_title") or "")
    abstract = str(record.get("abstract") or "")
    claims = str(record.get("claims") or "")
    description = str(record.get("description") or "")
    cpc = record.get("cpc_codes") or []

    text = (
        f"Title: {title}\n"
        f"CPC: {cpc}\n\n"
        f"Abstract:\n{abstract}\n\n"
        f"Claims:\n{claims}\n\n"
        f"Description:\n{description}"
    )
    return text[:max_chars]


def is_ai_candidate(record: dict[str, Any]) -> bool:
    haystack = " ".join(
        [
            str(record.get("invention_title") or ""),
            str(record.get("abstract") or ""),
            str(record.get("claims") or ""),
            str(record.get("description") or ""),
            " ".join([str(x) for x in (record.get("cpc_codes") or [])]),
        ]
    )
    return bool(AI_KEYWORD_PATTERN.search(haystack))


def build_prompt(record: dict[str, Any], text_payload: str) -> str:
    return (
        "You are a patent taxonomy analyst.\n"
        "Classify the patent and determine whether it is AI-driven.\n"
        "Use only evidence from the patent text provided.\n"
        "Return ONLY valid JSON with this exact schema and key order:\n"
        "{\n"
        '  "ai_driven": true/false,\n'
        '  "ai_type": "none|machine_learning|deep_learning|computer_vision|nlp|generative_ai|optimization_ai|autonomy_robotics|other_ai",\n'
        '  "patent_category": "adas_and_safety|vehicle_control_systems|manufacturing_process|materials_and_chemistry|tire_design_and_performance|telematics_and_sensing|enterprise_software_and_it|sustainability_and_energy|other",\n'
        '  "short_summary": "2-3 sentence summary",\n'
        '  "evidence_snippets": ["short quote 1", "short quote 2"],\n'
        '  "confidence": 0.0\n'
        "}\n"
        "Rules:\n"
        "- ai_driven must be false if no clear AI algorithm/modeling is central to the invention.\n"
        "- If AI is present but not central, set ai_driven=false and ai_type=none.\n"
        "- For generative content, use ai_type=generative_ai only when generation/model synthesis is core.\n"
        "- Keep evidence snippets short (<= 20 words each).\n"
        "- confidence is your confidence in ai_driven classification from 0 to 1.\n\n"
        f"Ticker: {record.get('ticker', '')}\n"
        f"Application number: {record.get('application_number', '')}\n"
        f"Invention title: {record.get('invention_title', '')}\n"
        f"Filing date: {record.get('filing_date', '')}\n\n"
        "Patent full text excerpt:\n"
        f"{text_payload}"
    )


def classify_patent(record: dict[str, Any], model: str, max_chars: int) -> dict[str, Any]:
    text_payload = build_text_payload(record, max_chars=max_chars)
    prompt = build_prompt(record, text_payload)
    raw = call_ollama(prompt=prompt, model=model, temperature=0.0)
    parsed = parse_json_object(raw)

    ai_driven = bool(parsed.get("ai_driven", False))
    ai_type = normalize_ai_type(parsed.get("ai_type", "none"))
    if not ai_driven:
        ai_type = "none"

    patent_category = normalize_category(parsed.get("patent_category", "other"))
    summary = str(parsed.get("short_summary") or "").strip()
    evidence = parsed.get("evidence_snippets")
    if not isinstance(evidence, list):
        evidence = []
    evidence = [str(x).strip() for x in evidence if str(x).strip()][:3]

    confidence_raw = parsed.get("confidence", 0.0)
    try:
        confidence = float(confidence_raw)
    except (TypeError, ValueError):
        confidence = 0.0
    confidence = max(0.0, min(1.0, confidence))

    return {
        "ai_driven": ai_driven,
        "ai_type": ai_type,
        "patent_category": patent_category,
        "short_summary": summary,
        "evidence_snippets": evidence,
        "confidence": confidence,
        "model_raw_output": raw,
    }


def build_non_ai_placeholder() -> dict[str, Any]:
    return {
        "ai_driven": False,
        "ai_type": "none",
        "patent_category": "other",
        "short_summary": "Not analyzed by Ollama because no AI candidate keywords were detected.",
        "evidence_snippets": [],
        "confidence": 0.0,
        "model_raw_output": "",
    }


def materialize_duckdb(db_path: Path, summary_df: pd.DataFrame, stats_df: pd.DataFrame) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()

    conn = duckdb.connect(str(db_path))
    conn.register("summary_df", summary_df)
    conn.execute("CREATE TABLE patent_ai_summaries AS SELECT * FROM summary_df")
    conn.unregister("summary_df")

    conn.register("stats_df", stats_df)
    conn.execute("CREATE TABLE patent_ai_company_stats AS SELECT * FROM stats_df")
    conn.unregister("stats_df")

    conn.execute("CREATE INDEX idx_patent_ai_ticker_app ON patent_ai_summaries(ticker, application_number)")
    conn.execute("CREATE INDEX idx_patent_ai_flags ON patent_ai_summaries(ai_driven, ai_type)")
    conn.execute("CREATE INDEX idx_patent_ai_stats_ticker ON patent_ai_company_stats(ticker)")
    conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize and categorize USPTO patents with Ollama")
    parser.add_argument("--model", default="qwen2.5:14b-instruct-q4_K_M", help="Ollama model")
    parser.add_argument("--tickers", default="", help="Comma-separated tickers. Default: all supported")
    parser.add_argument("--analyze-all", action="store_true", help="Analyze every patent row, not only AI candidates")
    parser.add_argument("--max-per-ticker", type=int, default=0, help="Limit records per ticker (0 = all)")
    parser.add_argument(
        "--max-candidates-per-ticker",
        type=int,
        default=0,
        help="Limit AI candidates analyzed per ticker (0 = all candidates)",
    )
    parser.add_argument("--max-chars", type=int, default=15000, help="Max patent text chars sent to model")
    parser.add_argument(
        "--db-path",
        default=str(OUT_DIR / "patent_ai_analyst.duckdb"),
        help="Output DuckDB path",
    )
    args = parser.parse_args()

    selected_tickers = [t.strip().upper() for t in args.tickers.split(",") if t.strip()]
    if not selected_tickers:
        selected_tickers = list(TICKER_TO_COMPANY.keys())

    unknown = [t for t in selected_tickers if t not in TICKER_TO_COMPANY]
    if unknown:
        raise ValueError(
            f"Unknown ticker(s): {', '.join(unknown)}. Supported: {', '.join(TICKER_TO_COMPANY.keys())}"
        )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    checkpoint_path = OUT_DIR / "patent_ai_summaries_ollama.jsonl"

    # Connectivity check
    _ = call_ollama("Reply with: OK", model=args.model, temperature=0.0)

    existing_keys: set[tuple[str, str]] = set()
    existing_rows: list[dict[str, Any]] = []
    if checkpoint_path.exists():
        for row in load_jsonl(checkpoint_path):
            ticker = str(row.get("ticker") or "")
            app_num = str(row.get("application_number") or "")
            if ticker and app_num:
                existing_keys.add((ticker, app_num))
                existing_rows.append(row)

    company_totals: dict[str, int] = {t: 0 for t in selected_tickers}
    company_candidates: dict[str, int] = {t: 0 for t in selected_tickers}

    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    checkpoint_handle = checkpoint_path.open("a", encoding="utf-8")

    for ticker in selected_tickers:
        source_path = RAW_DIR / ticker / "filings_with_text.jsonl"
        if not source_path.exists():
            print(f"WARN {ticker}: missing source file {source_path}")
            continue

        rows = load_jsonl(source_path)
        if args.max_per_ticker > 0:
            rows = rows[: args.max_per_ticker]

        candidate_counter = 0
        print(f"Processing {ticker}: {len(rows)} records")

        for row in rows:
            app_num = str(row.get("application_number") or "")
            if not app_num:
                continue

            company_totals[ticker] += 1
            ai_candidate = is_ai_candidate(row)
            if ai_candidate:
                company_candidates[ticker] += 1

            if not args.analyze_all and not ai_candidate:
                continue

            if args.max_candidates_per_ticker > 0 and ai_candidate:
                if candidate_counter >= args.max_candidates_per_ticker:
                    continue

            key = (ticker, app_num)
            if key in existing_keys:
                continue

            analyzed_at = datetime.now(timezone.utc).isoformat()
            model_result = classify_patent(row, model=args.model, max_chars=args.max_chars)

            out_row = {
                "ticker": ticker,
                "company": TICKER_TO_COMPANY[ticker],
                "application_number": app_num,
                "filing_date": row.get("filing_date"),
                "status_text": row.get("status_text"),
                "invention_title": row.get("invention_title"),
                "patent_number": row.get("patent_number"),
                "xml_source": row.get("xml_source"),
                "has_full_text": bool(row.get("abstract") or row.get("claims") or row.get("description")),
                "ai_candidate": ai_candidate,
                "ai_driven": model_result["ai_driven"],
                "ai_type": model_result["ai_type"],
                "patent_category": model_result["patent_category"],
                "short_summary": model_result["short_summary"],
                "evidence_snippets": json.dumps(model_result["evidence_snippets"], ensure_ascii=False),
                "confidence": model_result["confidence"],
                "model": args.model,
                "analyzed_at": analyzed_at,
                "model_raw_output": model_result["model_raw_output"],
            }
            checkpoint_handle.write(json.dumps(out_row, ensure_ascii=False) + "\n")
            checkpoint_handle.flush()
            existing_keys.add(key)

            candidate_counter += 1
            if candidate_counter <= 3 or candidate_counter % 20 == 0:
                print(
                    f"  analyzed {ticker} #{candidate_counter}: {app_num} | "
                    f"ai_driven={out_row['ai_driven']} ai_type={out_row['ai_type']}"
                )

    checkpoint_handle.close()

    # Reload consolidated rows from checkpoint and keep requested tickers only.
    all_rows = [
        r
        for r in load_jsonl(checkpoint_path)
        if str(r.get("ticker") or "") in selected_tickers
    ]

    summary_df = pd.DataFrame(all_rows)
    if summary_df.empty:
        summary_df = pd.DataFrame(
            columns=[
                "ticker",
                "company",
                "application_number",
                "filing_date",
                "status_text",
                "invention_title",
                "patent_number",
                "xml_source",
                "has_full_text",
                "ai_candidate",
                "ai_driven",
                "ai_type",
                "patent_category",
                "short_summary",
                "evidence_snippets",
                "confidence",
                "model",
                "analyzed_at",
                "model_raw_output",
            ]
        )

    # For aggregate AI counts, treat non-analyzed non-candidates as non-AI.
    stats_rows: list[dict[str, Any]] = []
    for ticker in selected_tickers:
        ticker_df = summary_df[summary_df["ticker"] == ticker] if not summary_df.empty else pd.DataFrame()
        total_patents = company_totals.get(ticker, 0)
        ai_candidates = company_candidates.get(ticker, 0)
        analyzed_patents = len(ticker_df)

        ai_patents = int((ticker_df["ai_driven"] == True).sum()) if analyzed_patents else 0
        ml_patents = int((ticker_df["ai_type"].isin(["machine_learning", "deep_learning"]).fillna(False)).sum()) if analyzed_patents else 0
        genai_patents = int((ticker_df["ai_type"] == "generative_ai").sum()) if analyzed_patents else 0
        cv_patents = int((ticker_df["ai_type"] == "computer_vision").sum()) if analyzed_patents else 0
        nlp_patents = int((ticker_df["ai_type"] == "nlp").sum()) if analyzed_patents else 0
        optimization_patents = int((ticker_df["ai_type"] == "optimization_ai").sum()) if analyzed_patents else 0
        autonomy_patents = int((ticker_df["ai_type"] == "autonomy_robotics").sum()) if analyzed_patents else 0

        ai_patent_share = (ai_patents / total_patents) if total_patents else 0.0

        stats_rows.append(
            {
                "ticker": ticker,
                "company": TICKER_TO_COMPANY[ticker],
                "total_patents": total_patents,
                "ai_candidates": ai_candidates,
                "analyzed_patents": analyzed_patents,
                "ai_patents": ai_patents,
                "ml_patents": ml_patents,
                "genai_patents": genai_patents,
                "computer_vision_patents": cv_patents,
                "nlp_patents": nlp_patents,
                "optimization_ai_patents": optimization_patents,
                "autonomy_robotics_patents": autonomy_patents,
                "ai_patent_share": round(ai_patent_share, 6),
            }
        )

    stats_df = pd.DataFrame(stats_rows)

    summary_csv_path = OUT_DIR / "patent_ai_summaries_ollama.csv"
    stats_csv_path = OUT_DIR / "patent_ai_company_stats.csv"

    summary_df.to_csv(summary_csv_path, index=False)
    stats_df.to_csv(stats_csv_path, index=False)

    materialize_duckdb(Path(args.db_path), summary_df, stats_df)

    print(f"Wrote {summary_csv_path} ({len(summary_df)} rows)")
    print(f"Wrote {stats_csv_path} ({len(stats_df)} rows)")
    print(f"Wrote {args.db_path}")
    print("Company AI summary:")
    for row in stats_rows:
        print(
            f"  {row['ticker']}: ai_patents={row['ai_patents']} / total_patents={row['total_patents']} "
            f"(share={row['ai_patent_share']:.2%}, analyzed={row['analyzed_patents']}, candidates={row['ai_candidates']})"
        )


if __name__ == "__main__":
    main()
