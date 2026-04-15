"""
PART 2 — Transcript Scraping
=============================
Scrapes pre-match press conference transcripts and stores them
in the SQLite database created by Part 1.

Two sources are attempted:
  1. asapsports.com  — the best public archive of ATP press conferences
  2. wtatennis.com   — backup for women's Grand Slam events

Install dependencies:
    pip install requests beautifulsoup4 tqdm lxml

Note on rate limiting:
    We add random delays between requests so we don't hammer the servers.
    For large-scale scraping consider using a proxy rotation service.

Usage:
    python part2_scraping.py
"""

import re
import time
import random
import sqlite3
import logging
from datetime import datetime
from urllib.parse import urljoin, urlencode, quote

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

# ── Config ────────────────────────────────────────────────────────────────────

DB_PATH     = "tennis_upsets.db"
DELAY_MIN   = 1.5   # seconds between requests (be polite)
DELAY_MAX   = 3.5
MAX_RETRIES = 3

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; TennisResearchBot/1.0; "
        "+https://github.com/your-repo)"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


# ── Database helpers ──────────────────────────────────────────────────────────

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


def ensure_transcript_table() -> None:
    """Create the transcripts table if it doesn't exist."""
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS transcripts (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            player_name  TEXT NOT NULL,
            player_id    INTEGER,
            tourney_name TEXT,
            tourney_date TEXT,
            round        TEXT,
            source_url   TEXT UNIQUE,
            scraped_at   TEXT,
            raw_text     TEXT
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_trans_player ON transcripts(player_name);")
    conn.commit()
    conn.close()


def transcript_exists(url: str) -> bool:
    conn = get_connection()
    row = conn.execute(
        "SELECT 1 FROM transcripts WHERE source_url=?", (url,)
    ).fetchone()
    conn.close()
    return row is not None


def save_transcript(record: dict) -> None:
    conn = get_connection()
    conn.execute("""
        INSERT OR IGNORE INTO transcripts
            (player_name, player_id, tourney_name, tourney_date,
             round, source_url, scraped_at, raw_text)
        VALUES
            (:player_name, :player_id, :tourney_name, :tourney_date,
             :round, :source_url, :scraped_at, :raw_text)
    """, record)
    conn.commit()
    conn.close()


# ── HTTP helpers ──────────────────────────────────────────────────────────────

def polite_get(url: str, retries: int = MAX_RETRIES) -> requests.Response | None:
    """GET with exponential back-off and politeness delay."""
    for attempt in range(1, retries + 1):
        time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))
        try:
            resp = requests.get(url, headers=HEADERS, timeout=20)
            resp.raise_for_status()
            return resp
        except requests.RequestException as exc:
            log.warning(f"Attempt {attempt}/{retries} failed for {url}: {exc}")
            time.sleep(2 ** attempt)  # exponential back-off

    log.error(f"Giving up on: {url}")
    return None


# ── ASAP Sports scraper ───────────────────────────────────────────────────────
#
#  ASAP Sports URL structure for press conferences:
#    https://www.asapsports.com/show_event.php?id=<EVENT_ID>
#    Individual interview pages:
#    https://www.asapsports.com/show_interview.php?id=<INTERVIEW_ID>
#
#  We first fetch the event index pages for each Grand Slam, then
#  follow links to individual player interview pages.

ASAP_BASE      = "https://www.asapsports.com"
ASAP_EVENT_URL = "https://www.asapsports.com/show_event.php"

# Map slam names to their typical ASAP event IDs (update as needed).
# You can find these by searching https://www.asapsports.com for "Australian Open 2023"
ASAP_EVENT_IDS = {
    # Format: "SLAM_YEAR": event_id
    # These are example IDs — look up current ones on asapsports.com
    "Australian Open 2023": 158001,
    "Roland Garros 2023":   159002,
    "Wimbledon 2023":       160003,
    "US Open 2023":         161004,
    "Australian Open 2022": 150001,
    "Roland Garros 2022":   151002,
    "Wimbledon 2022":       152003,
    "US Open 2022":         153004,
}

# Grand Slam name patterns used to detect press conference pages on ASAP
SLAM_KEYWORDS = [
    "australian open", "roland garros", "wimbledon", "us open",
    "french open",
]


def parse_asap_event_page(event_id: int, slam_name: str, slam_year: int) -> list[dict]:
    """
    Fetch an ASAP Sports event page and extract all interview links.
    Returns list of dicts: {url, player_name, round}
    """
    url = f"{ASAP_EVENT_URL}?id={event_id}"
    resp = polite_get(url)
    if resp is None:
        return []

    soup = BeautifulSoup(resp.text, "lxml")
    interviews = []

    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        if "show_interview" not in href:
            continue

        full_url = urljoin(ASAP_BASE, href)
        if transcript_exists(full_url):
            continue

        # Try to extract player name and round from surrounding text
        parent_text = a_tag.get_text(strip=True)
        row_text    = ""
        if a_tag.parent:
            row_text = a_tag.parent.get_text(separator=" ", strip=True)

        player_name = _extract_player_name(parent_text or row_text)
        round_name  = _extract_round(row_text)

        interviews.append({
            "url":         full_url,
            "player_name": player_name,
            "tourney_name": slam_name,
            "tourney_year": slam_year,
            "round":        round_name,
        })

    log.info(f"  Found {len(interviews)} interview links for {slam_name} {slam_year}")
    return interviews


def scrape_asap_interview(url: str, meta: dict) -> dict | None:
    """
    Fetch a single ASAP interview page and extract the transcript text.
    Returns a record dict ready for DB insertion, or None on failure.
    """
    resp = polite_get(url)
    if resp is None:
        return None

    soup = BeautifulSoup(resp.text, "lxml")

    # ASAP transcripts live in a <pre> block or a content <div>
    pre_block = soup.find("pre")
    if pre_block:
        raw_text = pre_block.get_text("\n", strip=False)
    else:
        # Fallback: grab the largest text block on the page
        content_div = _find_largest_text_div(soup)
        raw_text = content_div.get_text("\n", strip=False) if content_div else ""

    raw_text = _clean_transcript(raw_text)
    if len(raw_text) < 100:
        log.debug(f"  Transcript too short (<100 chars), skipping: {url}")
        return None

    # Try to refine player name from the transcript header
    player_name = meta.get("player_name") or _extract_player_name_from_transcript(raw_text)

    return {
        "player_name":  player_name,
        "player_id":    None,  # will be linked in Part 4
        "tourney_name": meta.get("tourney_name"),
        "tourney_date": str(meta.get("tourney_year")),
        "round":        meta.get("round"),
        "source_url":   url,
        "scraped_at":   datetime.utcnow().isoformat(),
        "raw_text":     raw_text,
    }


# ── WTA backup scraper ────────────────────────────────────────────────────────

WTA_SEARCH_URL = "https://www.wtatennis.com/news/search"


def scrape_wta_transcripts(player_name: str, slam_name: str) -> list[dict]:
    """
    Very basic WTA news search scraper.
    Searches for press-conference articles mentioning the player + slam.
    This is a best-effort fallback; the HTML structure may change.
    """
    results = []
    query   = f"{player_name} {slam_name} press conference"
    url     = f"{WTA_SEARCH_URL}?{urlencode({'q': query})}"

    resp = polite_get(url)
    if resp is None:
        return results

    soup = BeautifulSoup(resp.text, "lxml")
    for article_link in soup.select("a[href*='/news/']")[:5]:
        article_url = urljoin("https://www.wtatennis.com", article_link["href"])
        if transcript_exists(article_url):
            continue

        article_resp = polite_get(article_url)
        if not article_resp:
            continue

        article_soup = BeautifulSoup(article_resp.text, "lxml")
        body_div     = article_soup.find("div", class_=re.compile(r"article|content|body", re.I))
        raw_text     = body_div.get_text("\n") if body_div else ""
        raw_text     = _clean_transcript(raw_text)

        if len(raw_text) < 200:
            continue

        results.append({
            "player_name":  player_name,
            "player_id":    None,
            "tourney_name": slam_name,
            "tourney_date": None,
            "round":        None,
            "source_url":   article_url,
            "scraped_at":   datetime.utcnow().isoformat(),
            "raw_text":     raw_text,
        })

    return results


# ── Text utilities ────────────────────────────────────────────────────────────

def _clean_transcript(text: str) -> str:
    """Remove boilerplate, excess whitespace, and HTML artefacts."""
    # Remove HTML entities that slipped through
    text = re.sub(r"&[a-zA-Z]+;", " ", text)
    text = re.sub(r"&#\d+;",       " ", text)
    # Remove ASAP header boilerplate
    text = re.sub(r"FastScripts.*", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"Copyright.*",   "", text, flags=re.DOTALL | re.IGNORECASE)
    # Collapse whitespace
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r" {2,}",  " ",    text)
    return text.strip()


def _extract_player_name(text: str) -> str:
    """
    Best-effort name extraction from a line of text.
    Looks for patterns like "NOVAK DJOKOVIC" (all-caps) or "Djokovic, Novak".
    """
    # All-caps full name (common in ASAP transcripts)
    m = re.search(r"\b([A-Z]{2,}\s+[A-Z]{2,})\b", text)
    if m:
        return m.group(1).title()
    # Last, First format
    m = re.search(r"([A-Z][a-z]+),\s+([A-Z][a-z]+)", text)
    if m:
        return f"{m.group(2)} {m.group(1)}"
    # Fallback: first two title-case words
    words = [w for w in text.split() if w[0].isupper()] if text else []
    return " ".join(words[:2]) if len(words) >= 2 else text[:40]


def _extract_player_name_from_transcript(text: str) -> str:
    """Parse the first few lines of a transcript for a speaker name."""
    for line in text.split("\n")[:10]:
        line = line.strip()
        # Lines like "AN INTERVIEW WITH: RAFAEL NADAL"
        m = re.match(r"AN INTERVIEW WITH[:\s]+(.+)", line, re.IGNORECASE)
        if m:
            return m.group(1).title().strip()
        # All-caps short line = likely a name header
        if re.match(r"^[A-Z\s]{5,40}$", line):
            return line.title().strip()
    return "Unknown"


def _extract_round(text: str) -> str:
    """Extract match round from surrounding text."""
    round_map = {
        r"\bfirst round\b|\br1\b|\b1r\b":          "R1",
        r"\bsecond round\b|\br2\b|\b2r\b":         "R2",
        r"\bthird round\b|\br3\b|\b3r\b":          "R3",
        r"\bfourth round\b|\br4\b|\b4r\b":         "R4",
        r"\bquarterfinale?\b|\bqf\b":              "QF",
        r"\bsemifinale?\b|\bsf\b":                 "SF",
        r"\bfinal\b|\bf\b":                        "F",
    }
    text_lower = text.lower()
    for pattern, label in round_map.items():
        if re.search(pattern, text_lower):
            return label
    return "Unknown"


def _find_largest_text_div(soup: BeautifulSoup):
    """Find the <div> with the most text content as a fallback."""
    divs = soup.find_all("div")
    if not divs:
        return None
    return max(divs, key=lambda d: len(d.get_text()))


# ── Player-match linking ──────────────────────────────────────────────────────

def link_transcripts_to_players() -> None:
    """
    After scraping, attempt to match transcript player names to player IDs
    in the players table using fuzzy name matching.
    """
    conn = get_connection()

    players = conn.execute(
        "SELECT player_id, full_name FROM players"
    ).fetchall()

    if not players:
        log.warning("No players table found — skipping linking step.")
        conn.close()
        return

    # Build a simple lookup: lowercase name → player_id
    name_to_id = {name.lower(): pid for pid, name in players}

    unlinked = conn.execute(
        "SELECT id, player_name FROM transcripts WHERE player_id IS NULL"
    ).fetchall()

    linked_count = 0
    for row_id, player_name in unlinked:
        # Exact lowercase match
        pid = name_to_id.get(player_name.lower())

        # Fallback: last name match
        if pid is None:
            last_name = player_name.split()[-1].lower() if player_name else ""
            candidates = [(n, i) for n, i in name_to_id.items() if last_name in n]
            if len(candidates) == 1:
                pid = candidates[0][1]

        if pid:
            conn.execute(
                "UPDATE transcripts SET player_id=? WHERE id=?",
                (pid, row_id),
            )
            linked_count += 1

    conn.commit()
    conn.close()
    log.info(f"Linked {linked_count}/{len(unlinked)} transcripts to player IDs.")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 60)
    print("  PART 2 — Transcript Scraping")
    print("=" * 60)

    ensure_transcript_table()

    total_saved = 0

    for event_label, event_id in tqdm(ASAP_EVENT_IDS.items(), desc="Events"):
        parts     = event_label.rsplit(" ", 1)
        slam_name = parts[0]
        slam_year = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 2023

        log.info(f"\nScraping: {event_label}")
        interviews = parse_asap_event_page(event_id, slam_name, slam_year)

        for meta in tqdm(interviews, desc=f"  Interviews ({event_label})", leave=False):
            record = scrape_asap_interview(meta["url"], meta)
            if record:
                save_transcript(record)
                total_saved += 1

    log.info("\nLinking transcripts to player IDs …")
    link_transcripts_to_players()

    # Summary
    conn = get_connection()
    n_total  = conn.execute("SELECT COUNT(*) FROM transcripts").fetchone()[0]
    n_linked = conn.execute(
        "SELECT COUNT(*) FROM transcripts WHERE player_id IS NOT NULL"
    ).fetchone()[0]
    conn.close()

    print(f"\n── Scraping summary ──────────────────────────")
    print(f"  Transcripts saved this run : {total_saved:,}")
    print(f"  Total in database          : {n_total:,}")
    print(f"  Linked to player ID        : {n_linked:,}")
    print(f"─────────────────────────────────────────────")
    print("\nPart 2 complete. Run part3_nlp.py next.")


if __name__ == "__main__":
    main()