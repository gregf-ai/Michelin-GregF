"""Download US patent filings from USPTO ODP with full text from XML bulk data.

The ODP search API returns metadata per filing.  Each record includes
pgpubDocumentMetaData and/or grantDocumentMetaData which contain a
fileLocationURI pointing to a per-application XML file with the full text
(abstract, claims, description).  This script downloads those XMLs and
extracts the text — no PDF parsing required.

Outputs are written under data/raw/uspto_odp/<TICKER>/:
- filings_raw.jsonl           raw filing metadata records from ODP search
- filings_with_text.jsonl     filing + abstract + claims + description text

Usage:
    python data/extract/download_uspto_odp_filings.py
    python data/extract/download_uspto_odp_filings.py --max-records-per-company 5
"""

from __future__ import annotations

import argparse
import json
import os
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests

API_BASE = "https://api.uspto.gov/api/v1"
DATA_ROOT = Path(__file__).resolve().parents[1]
RAW_OUT = DATA_ROOT / "raw" / "uspto_odp"
ENV_FILE = DATA_ROOT.parent / ".env"

COMPANY_QUERIES = {
    "MGDDY": "(applicationMetaData.firstApplicantName:Michelin* OR applicationMetaData.firstApplicantName:Compagnie*Michelin*)",
    "GT": "(applicationMetaData.firstApplicantName:Goodyear* OR applicationMetaData.firstApplicantName:*Goodyear*Tire*)",
    "BRDCY": "(applicationMetaData.firstApplicantName:Bridgestone*)",
    "CTTAY": "(applicationMetaData.firstApplicantName:Continental* OR applicationMetaData.firstApplicantName:*Continental*AG*)",
    "PLLIF": "(applicationMetaData.firstApplicantName:Pirelli*)",
    "SSUMY": "(applicationMetaData.firstApplicantName:Sumitomo*Rubber* OR applicationMetaData.firstApplicantName:Sumitomo*)",
}

SEARCH_FIELDS = (
    "applicationNumberText,"
    "applicationMetaData,"
    "pgpubDocumentMetaData,"
    "grantDocumentMetaData"
)

MAX_RETRIES = 5


def read_odp_key() -> str:
    key = os.getenv("ODP_API_KEY", "").strip()
    if key:
        return key

    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8", errors="ignore").splitlines():
            if line.strip().startswith("ODP_API_KEY="):
                value = line.split("=", 1)[1].strip()
                if value:
                    return value

    raise RuntimeError("ODP_API_KEY not found. Set env var or add it to .env")


def sanitize_filename(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {".", "_", "-"} else "_" for ch in value)


def get_with_retries(session: requests.Session, url: str, **kwargs: Any) -> requests.Response:
    delay = 1.0
    for attempt in range(MAX_RETRIES):
        response = session.get(url, **kwargs)
        if response.status_code != 429:
            response.raise_for_status()
            return response
        if attempt == MAX_RETRIES - 1:
            response.raise_for_status()
        time.sleep(delay)
        delay *= 2
    raise RuntimeError(f"Exceeded retry budget for {url}")


# ── XML text extraction helpers ──────────────────────────────────────────────

def _iter_text(el: ET.Element | None) -> str:
    """Recursively extract all text from an XML element tree."""
    if el is None:
        return ""
    parts: list[str] = []
    for node in el.iter():
        if node.text:
            parts.append(node.text.strip())
        if node.tail:
            parts.append(node.tail.strip())
    return " ".join(p for p in parts if p)


def _extract_abstract(root: ET.Element) -> str:
    ab = root.find(".//abstract")
    return _iter_text(ab)


def _extract_claims(root: ET.Element) -> str:
    claims_el = root.find(".//claims")
    if claims_el is None:
        return ""
    parts = []
    for claim in claims_el.findall(".//claim"):
        parts.append(_iter_text(claim))
    return "\n".join(parts)


def _extract_description(root: ET.Element) -> str:
    desc = root.find(".//description")
    return _iter_text(desc)


def fetch_xml_text(session: requests.Session, uri: str, xml_path: Path) -> dict[str, str]:
    """Download a patent XML, save it locally, and return abstract/claims/description."""
    try:
        r = get_with_retries(session, uri, timeout=120)
        xml_path.parent.mkdir(parents=True, exist_ok=True)
        xml_path.write_bytes(r.content)
        root = ET.fromstring(r.content)
        return {
            "abstract": _extract_abstract(root),
            "claims": _extract_claims(root),
            "description": _extract_description(root),
        }
    except Exception as exc:
        print(f"  XML fetch failed for {uri}: {exc}")
        return {"abstract": "", "claims": "", "description": ""}


# ── main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Download US patent filings with full text from ODP")
    parser.add_argument("--from-date", default="2010-01-01", help="Filing date start (YYYY-MM-DD)")
    parser.add_argument("--to-date", default="2026-12-31", help="Filing date end (YYYY-MM-DD)")
    parser.add_argument("--page-size", type=int, default=100, help="ODP page size")
    parser.add_argument("--max-records-per-company", type=int, default=0, help="0 means all")
    parser.add_argument("--sleep", type=float, default=0.1, help="Delay between API calls")
    parser.add_argument(
        "--tickers",
        default="",
        help="Comma-separated subset of tickers to process (e.g., CTTAY,PLLIF,SSUMY). Default: all",
    )
    args = parser.parse_args()

    key = read_odp_key()

    RAW_OUT.mkdir(parents=True, exist_ok=True)

    session = requests.Session()
    session.headers.update({"X-API-KEY": key})

    selected_tickers = [t.strip().upper() for t in args.tickers.split(",") if t.strip()]
    if selected_tickers:
        unknown_tickers = [t for t in selected_tickers if t not in COMPANY_QUERIES]
        if unknown_tickers:
            raise ValueError(
                f"Unknown ticker(s): {', '.join(unknown_tickers)}. "
                f"Supported: {', '.join(COMPANY_QUERIES.keys())}"
            )
        company_items = [(ticker, COMPANY_QUERIES[ticker]) for ticker in selected_tickers]
    else:
        company_items = list(COMPANY_QUERIES.items())

    for ticker, query_core in company_items:
        out_dir = RAW_OUT / ticker
        docs_dir = out_dir / "documents"
        out_dir.mkdir(parents=True, exist_ok=True)
        docs_dir.mkdir(parents=True, exist_ok=True)

        raw_path = out_dir / "filings_raw.jsonl"
        full_path = out_dir / "filings_with_text.jsonl"

        total_saved = 0
        offset = 0

        print(f"\n=== {ticker} ===")

        with raw_path.open("w", encoding="utf-8") as raw_f, full_path.open("w", encoding="utf-8") as full_f:
            while True:
                q = f"{query_core} AND applicationMetaData.filingDate:[{args.from_date} TO {args.to_date}]"
                params = {
                    "q": q,
                    "limit": args.page_size,
                    "offset": offset,
                    "fields": SEARCH_FIELDS,
                }

                try:
                    r = get_with_retries(session, f"{API_BASE}/patent/applications/search", params=params, timeout=90)
                    data = r.json()
                except Exception as exc:
                    print(f"Search error at offset {offset}: {exc}")
                    break

                rows = data.get("patentFileWrapperDataBag", []) if isinstance(data, dict) else []
                if not rows:
                    break

                for row in rows:
                    app_num = row.get("applicationNumberText", "")
                    meta = row.get("applicationMetaData", {}) or {}

                    filing_date = meta.get("filingDate", "")
                    status_code = meta.get("applicationStatusCode", "")
                    status_text = meta.get("applicationStatusDescriptionText", "")

                    raw_record = {
                        "ticker": ticker,
                        "application_number": app_num,
                        "filing_date": filing_date,
                        "status_code": status_code,
                        "status_text": status_text,
                        "application_type": meta.get("applicationTypeLabelName", ""),
                        "first_applicant_name": meta.get("firstApplicantName", ""),
                        "invention_title": meta.get("inventionTitle", ""),
                        "cpc_codes": meta.get("cpcClassificationBag", []),
                        "grant_date": meta.get("grantDate", ""),
                        "patent_number": meta.get("patentNumber", ""),
                        "raw": row,
                    }
                    raw_f.write(json.dumps(raw_record, ensure_ascii=False) + "\n")

                    # Prefer grant XML (more complete); fall back to pgpub XML
                    grant_meta = row.get("grantDocumentMetaData") or {}
                    pgpub_meta = row.get("pgpubDocumentMetaData") or {}
                    xml_uri = grant_meta.get("fileLocationURI") or pgpub_meta.get("fileLocationURI") or ""
                    xml_source = "grant" if grant_meta.get("fileLocationURI") else ("pgpub" if xml_uri else "none")
                    xml_name = grant_meta.get("xmlFileName") or pgpub_meta.get("xmlFileName") or ""
                    if not xml_name and xml_uri:
                        xml_name = Path(urlparse(xml_uri).path).name
                    xml_path = docs_dir / sanitize_filename(xml_name or f"{app_num}_{xml_source}.xml")

                    texts = {"abstract": "", "claims": "", "description": ""}
                    if xml_uri:
                        texts = fetch_xml_text(session, xml_uri, xml_path)

                    full_record = {
                        "ticker": ticker,
                        "application_number": app_num,
                        "filing_date": filing_date,
                        "status_code": status_code,
                        "status_text": status_text,
                        "invention_title": meta.get("inventionTitle", ""),
                        "grant_date": meta.get("grantDate", ""),
                        "patent_number": meta.get("patentNumber", ""),
                        "cpc_codes": meta.get("cpcClassificationBag", []),
                        "xml_source": xml_source,
                        "xml_uri": xml_uri,
                        "xml_path": str(xml_path) if xml_uri else "",
                        "abstract": texts["abstract"],
                        "claims": texts["claims"],
                        "description": texts["description"],
                    }
                    full_f.write(json.dumps(full_record, ensure_ascii=False) + "\n")

                    label = "✓" if texts["abstract"] else "·"
                    total_saved += 1
                    if total_saved % 10 == 0 or total_saved <= 3:
                        print(f"  {label} {total_saved}: {app_num} ({filing_date}) [{xml_source}]")

                    if args.max_records_per_company > 0 and total_saved >= args.max_records_per_company:
                        break

                    time.sleep(args.sleep)

                if args.max_records_per_company > 0 and total_saved >= args.max_records_per_company:
                    break

                offset += len(rows)
                if len(rows) < args.page_size:
                    break

        print(f"Completed {ticker}: {total_saved} filings")

    print(f"\nDone. Raw ODP data written to {RAW_OUT}")


if __name__ == "__main__":
    main()
