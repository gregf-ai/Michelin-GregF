"""Parse manual transcript txt files and merge them into raw transcript JSON.

This script auto-discovers files in data/raw/transcripts/manual matching the
pattern <ticker>_q<quarter>_<year>.txt and appends any missing transcripts to
the corresponding raw JSON file without overwriting existing entries.
"""
import json
import re
from datetime import datetime
from pathlib import Path

MANUAL_DIR = Path(__file__).parent / "raw/transcripts/manual"
RAW_TRANSCRIPTS_DIR = Path(__file__).parent / "raw/transcripts"
MANUAL_FILENAME_RE = re.compile(r"^(?P<ticker>[a-z0-9]+)_q(?P<quarter>[1-4])_(?P<year>\d{4})\.txt$", re.IGNORECASE)
HEADER_DATE_RE = re.compile(r"([A-Z][a-z]+\s+\d{1,2},\s+\d{4}\s+\d{1,2}:\d{2}\s+[AP]M)\s+(?:ET|EST|EDT)")

# Section headers to skip
SECTION_HEADERS = {
    "Presentation", "Question-and-Answer Session", "Operator Instructions",
    "[Operator Instructions]", "Company Participants", "Conference Call Participants",
}


def collect_participants(lines):
    """Extract participant names from the header section."""
    participants = {"Operator"}
    for line in lines:
        stripped = line.strip()
        if " - " in stripped and stripped:
            name = stripped.split(" - ")[0].strip()
            if name:
                participants.add(name)
    return participants


def find_content_start(lines):
    """Find the index where actual transcript content begins (after participant lists)."""
    last_participant_line = -1
    for i, line in enumerate(lines):
        if " - " in line.strip() and line.strip():
            last_participant_line = i

    if last_participant_line == -1:
        return 0

    # Skip blank lines after participant list to find first speaker line
    i = last_participant_line + 1
    while i < len(lines) and lines[i].strip() == "":
        i += 1
    return i


def looks_like_name(text):
    """Return True if text looks like a person's name or 'Operator'."""
    text = text.strip()
    if not text:
        return False
    if text == "Operator":
        return True
    # Names have titlecase words, no period, relatively short, no lowercase start
    if len(text) > 60:
        return False
    if text[0].islower():
        return False
    # Check it's not clearly a sentence (no period mid-text)
    if re.search(r'\.\s+[A-Z]', text):
        return False
    # Should have at least one space (first name + last name)
    words = text.split()
    if len(words) < 1:
        return False
    # All words should start uppercase or be common conjunctions
    title_words = sum(1 for w in words if w[0].isupper() or w.lower() in ('and', 'de', 'van', 'der'))
    return title_words >= len(words) - 1


def is_title_line(text, previous_was_name):
    """Return True if this looks like a job title or company affiliation line."""
    if not previous_was_name:
        return False
    text = text.strip()
    if not text:
        return False
    # Title lines: short, often contain commas or specific keywords
    if len(text) > 100:
        return False
    title_keywords = ['CEO', 'CFO', 'Managing', 'Director', 'Officer', 'Analyst',
                      'Research', 'Division', 'S.p.A.', 'SIM', 'LLC', 'Chase',
                      'Sanpaolo', 'Bernstein', 'Deutsche', 'Exane', 'Securities',
                      'Goldman', 'Morgan', 'JPMorgan', 'BNP', 'BofA', 'General Manager',
                      'Partner', 'Chairman']
    text_lower = text.lower()
    for kw in title_keywords:
        if kw.lower() in text_lower:
            return True
    # Also check: mixed case, contains commas (like role descriptions)
    if ',' in text and len(text) < 80:
        return True
    return False


def parse_transcript(filepath, participants):
    """Parse transcript txt file into 'Speaker: text\\n' format."""
    with open(filepath, 'r', encoding='utf-8') as f:
        raw = f.read()

    lines = raw.split('\n')
    content_start = find_content_start(lines)
    content_lines = lines[content_start:]

    # Build a list of (speaker, text) pairs
    segments = []
    current_speaker = None
    current_text_parts = []
    prev_was_name = False

    i = 0
    while i < len(content_lines):
        line = content_lines[i].rstrip()
        stripped = line.strip()

        # Skip section headers
        if stripped in SECTION_HEADERS or stripped.startswith('[Operator Instructions]'):
            prev_was_name = False
            i += 1
            continue

        if stripped == '':
            prev_was_name = False
            i += 1
            continue

        # Check if this line is a speaker name (known participant or looks like a name)
        is_speaker_line = stripped in participants or (
            stripped not in SECTION_HEADERS and looks_like_name(stripped)
        )

        # Check if this is a title/affiliation line (after a speaker name)
        if prev_was_name and is_title_line(stripped, prev_was_name):
            # Skip title line, keep current_speaker
            prev_was_name = False
            i += 1
            continue

        if is_speaker_line:
            # Save previous speaker's content
            if current_speaker and current_text_parts:
                text = ' '.join(
                    part.strip() for part in current_text_parts if part.strip()
                )
                segments.append((current_speaker, text))
            current_speaker = stripped
            current_text_parts = []
            prev_was_name = True
            i += 1
            continue

        # Regular text line - accumulate for current speaker
        if current_speaker:
            current_text_parts.append(stripped)
        prev_was_name = False
        i += 1

    # Flush last speaker
    if current_speaker and current_text_parts:
        text = ' '.join(part.strip() for part in current_text_parts if part.strip())
        segments.append((current_speaker, text))

    # Format as "Speaker: text\n" joined
    content = '\n'.join(f"{speaker}: {text}" for speaker, text in segments)
    return content


def discover_manual_files() -> list[tuple[Path, dict[str, int | str]]]:
    discovered: list[tuple[Path, dict[str, int | str]]] = []
    for filepath in sorted(MANUAL_DIR.glob("*.txt")):
        match = MANUAL_FILENAME_RE.match(filepath.name)
        if not match:
            print(f"Skipping {filepath.name} (filename does not match expected pattern)")
            continue
        ticker = match.group("ticker").upper()
        quarter = int(match.group("quarter"))
        year = int(match.group("year"))
        discovered.append(
            (
                filepath,
                {
                    "ticker": ticker,
                    "year": year,
                    "quarter": quarter,
                },
            )
        )
    return discovered


def extract_call_datetime(filepath: Path) -> str | None:
    with open(filepath, "r", encoding="utf-8") as f:
        for _ in range(5):
            line = f.readline()
            if not line:
                break
            match = HEADER_DATE_RE.search(line)
            if match:
                parsed = datetime.strptime(match.group(1), "%B %d, %Y %I:%M %p")
                return parsed.strftime("%Y-%m-%d %H:%M:%S")
    return None


def main():
    manual_files = discover_manual_files()
    if not manual_files:
        print("No manual transcript files found.")
        return

    updates_by_ticker: dict[str, list[dict[str, object]]] = {}
    repaired_by_ticker: dict[str, int] = {}

    for filepath, meta in manual_files:
        ticker = str(meta["ticker"])
        year = int(meta["year"])
        quarter = int(meta["quarter"])
        json_path = RAW_TRANSCRIPTS_DIR / f"{ticker}.json"

        if json_path.exists():
            with open(json_path, "r", encoding="utf-8") as f:
                existing = json.load(f)
            if not isinstance(existing, list):
                existing = []
        else:
            existing = []

        print(f"Parsing {filepath.name}...")
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.read().split("\n")

        participants = collect_participants(lines)
        participants.add("Operator")
        print(f"  Participants: {sorted(participants)}")

        content = parse_transcript(filepath, participants)
        speaker_count = content.count("\n") + 1 if content else 0
        transcript_date = extract_call_datetime(filepath)
        print(f"  Parsed {speaker_count} speaker segments, {len(content)} chars")

        existing_entry = next(
            (
                entry
                for entry in existing
                if isinstance(entry, dict)
                and entry.get("year") == year
                and entry.get("quarter") == quarter
            ),
            None,
        )
        if existing_entry is not None:
            updated = False
            if not existing_entry.get("date") and transcript_date:
                existing_entry["date"] = transcript_date
                updated = True
            if not existing_entry.get("content") and content:
                existing_entry["content"] = content
                updated = True
            if updated:
                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump(existing, f, ensure_ascii=False, indent=2)
                repaired_by_ticker[ticker] = repaired_by_ticker.get(ticker, 0) + 1
                print(f"  Repaired existing {ticker} {year} Q{quarter} entry")
            else:
                print(f"Skipping {filepath.name} ({ticker} {year} Q{quarter} already in JSON)")
            continue

        entry = {
            "symbol": ticker,
            "year": year,
            "quarter": quarter,
            "date": transcript_date,
            "content": content,
        }
        updates_by_ticker.setdefault(ticker, []).append(entry)

    if not updates_by_ticker:
        print("No new entries to add.")
        return

    total_added = 0
    for ticker, new_entries in updates_by_ticker.items():
        json_path = RAW_TRANSCRIPTS_DIR / f"{ticker}.json"
        if json_path.exists():
            with open(json_path, "r", encoding="utf-8") as f:
                existing = json.load(f)
            if not isinstance(existing, list):
                existing = []
        else:
            existing = []

        combined = existing + new_entries
        combined.sort(key=lambda x: (x.get("year", 0), x.get("quarter", 0)), reverse=True)

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(combined, f, ensure_ascii=False, indent=2)

        total_added += len(new_entries)
        print(f"Added {len(new_entries)} entries to {json_path.name}. Total: {len(combined)}")

    for ticker, repaired_count in repaired_by_ticker.items():
        print(f"Repaired {repaired_count} existing entries in {ticker}.json")

    print(
        f"\nDone. Added {total_added} new entries across {len(updates_by_ticker)} ticker(s) "
        f"and repaired {sum(repaired_by_ticker.values())} existing entries."
    )


if __name__ == '__main__':
    main()
