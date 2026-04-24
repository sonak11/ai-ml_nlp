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

# configuration

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


# database helpers 

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


# HTTP helpers 

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


# ASAP Sports scraper
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
    "Australian Open 2021": 100001,
	"Roland Garros 2021": 100002,
	"Wimbledon 2021": 100003,
	"US Open 2021": 100004,
	"PRESS CONFERENCES 2021": 100005,
	"BRISBANE INTERNATIONAL 2021": 100006,
	"UNITED CUP 2021": 100007,
	"DAVIS CUP FINALS 2021": 100008,
	"BILLIE JEAN KING CUP 2021": 100009,
	"NITTO ATP FINALS 2021": 100010,
	"ROLEX PARIS MASTERS 2021": 100011,
	"WTA FINALS 2021": 100012,
	"ROLEX SHANGHAI MASTERS 2021": 100013,
	"CHINA OPEN 2021": 100014,
	"LAVER CUP 2021": 100015,
	"NATIONAL BANK OPEN 2021": 100016,
	"OMNIUM BANQUE NATIONALE 2021": 100017,
	"MUBADALA CITI DC OPEN 2021": 100018,
	"INTERNATIONAL TENNIS HALL OF FAME 2021": 100019,
	"THE CHAMPIONSHIPS 2021": 100020,
	"ROTHESAY INTERNATIONAL 2021": 100021,
	"CINCH CHAMPIONSHIPS 2021": 100022,
	"INTERNAZIONALI BNL D'ITALIA 2021": 100023,
	"MUTUA MADRID OPEN 2021": 100024,
	"PORSCHE TENNIS GRAND PRIX 2021": 100025,
	"ROLEX MONTE-CARLO MASTERS 2021": 100026,
	"BILLIE JEAN KING CUP: USA VS BELGIUM 2021": 100027,
	"MIAMI OPEN PRESENTED BY ITAú 2021": 100028,
	"BNP PARIBAS OPEN 2021": 100029,
	"DUBAI DUTY FREE TENNIS CHAMPIONSHIPS 2021": 100030,
	"QATAR EXXONMOBIL OPEN 2021": 100031,
	"QATAR TOTAL ENERGIES OPEN 2021": 100032,
	"ADELAIDE INTERNATIONAL 2021": 100033,

	"Australian Open 2022": 100034,
	"Roland Garros 2022": 100035,
	"Wimbledon 2022": 100036,
	"US Open 2022": 100037,
	"PRESS CONFERENCES 2022": 100038,
	"BRISBANE INTERNATIONAL 2022": 100039,
	"UNITED CUP 2022": 100040,
	"DAVIS CUP FINALS 2022": 100041,
	"BILLIE JEAN KING CUP 2022": 100042,
	"NITTO ATP FINALS 2022": 100043,
	"ROLEX PARIS MASTERS 2022": 100044,
	"WTA FINALS 2022": 100045,
	"ROLEX SHANGHAI MASTERS 2022": 100046,
	"CHINA OPEN 2022": 100047,
	"LAVER CUP 2022": 100048,
	"NATIONAL BANK OPEN 2022": 100049,
	"OMNIUM BANQUE NATIONALE 2022": 100050,
	"MUBADALA CITI DC OPEN 2022": 100051,
	"INTERNATIONAL TENNIS HALL OF FAME 2022": 100052,
	"THE CHAMPIONSHIPS 2022": 100053,
	"ROTHESAY INTERNATIONAL 2022": 100054,
	"CINCH CHAMPIONSHIPS 2022": 100055,
	"INTERNAZIONALI BNL D'ITALIA 2022": 100056,
	"MUTUA MADRID OPEN 2022": 100057,
	"PORSCHE TENNIS GRAND PRIX 2022": 100058,
	"ROLEX MONTE-CARLO MASTERS 2022": 100059,
	"BILLIE JEAN KING CUP: USA VS BELGIUM 2022": 100060,
	"MIAMI OPEN PRESENTED BY ITAú 2022": 100061,
	"BNP PARIBAS OPEN 2022": 100062,
	"DUBAI DUTY FREE TENNIS CHAMPIONSHIPS 2022": 100063,
	"QATAR EXXONMOBIL OPEN 2022": 100064,
	"QATAR TOTAL ENERGIES OPEN 2022": 100065,
	"ADELAIDE INTERNATIONAL 2022": 100066,

	"Australian Open 2023": 100067,
	"Roland Garros 2023": 100068,
	"Wimbledon 2023": 100069,
	"US Open 2023": 100070,
	"PRESS CONFERENCES 2023": 100071,
	"BRISBANE INTERNATIONAL 2023": 100072,
	"UNITED CUP 2023": 100073,
	"DAVIS CUP FINALS 2023": 100074,
	"BILLIE JEAN KING CUP 2023": 100075,
	"NITTO ATP FINALS 2023": 100076,
	"ROLEX PARIS MASTERS 2023": 100077,
	"WTA FINALS 2023": 100078,
	"ROLEX SHANGHAI MASTERS 2023": 100079,
	"CHINA OPEN 2023": 100080,
	"LAVER CUP 2023": 100081,
	"NATIONAL BANK OPEN 2023": 100082,
	"OMNIUM BANQUE NATIONALE 2023": 100083,
	"MUBADALA CITI DC OPEN 2023": 100084,
	"INTERNATIONAL TENNIS HALL OF FAME 2023": 100085,
	"THE CHAMPIONSHIPS 2023": 100086,
	"ROTHESAY INTERNATIONAL 2023": 100087,
	"CINCH CHAMPIONSHIPS 2023": 100088,
	"INTERNAZIONALI BNL D'ITALIA 2023": 100089,
	"MUTUA MADRID OPEN 2023": 100090,
	"PORSCHE TENNIS GRAND PRIX 2023": 100091,
	"ROLEX MONTE-CARLO MASTERS 2023": 100092,
	"BILLIE JEAN KING CUP: USA VS BELGIUM 2023": 100093,
	"MIAMI OPEN PRESENTED BY ITAú 2023": 100094,
	"BNP PARIBAS OPEN 2023": 100095,
	"DUBAI DUTY FREE TENNIS CHAMPIONSHIPS 2023": 100096,
	"QATAR EXXONMOBIL OPEN 2023": 100097,
	"QATAR TOTAL ENERGIES OPEN 2023": 100098,
	"ADELAIDE INTERNATIONAL 2023": 100099,

	"Australian Open 2024": 100100,
	"Roland Garros 2024": 100101,
	"Wimbledon 2024": 100102,
	"US Open 2024": 100103,
	"PRESS CONFERENCES 2024": 100104,
	"BRISBANE INTERNATIONAL 2024": 100105,
	"UNITED CUP 2024": 100106,
	"DAVIS CUP FINALS 2024": 100107,
	"BILLIE JEAN KING CUP 2024": 100108,
	"NITTO ATP FINALS 2024": 100109,
	"ROLEX PARIS MASTERS 2024": 100110,
	"WTA FINALS 2024": 100111,
	"ROLEX SHANGHAI MASTERS 2024": 100112,
	"CHINA OPEN 2024": 100113,
	"LAVER CUP 2024": 100114,
	"NATIONAL BANK OPEN 2024": 100115,
	"OMNIUM BANQUE NATIONALE 2024": 100116,
	"MUBADALA CITI DC OPEN 2024": 100117,
	"INTERNATIONAL TENNIS HALL OF FAME 2024": 100118,
	"THE CHAMPIONSHIPS 2024": 100119,
	"ROTHESAY INTERNATIONAL 2024": 100120,
	"CINCH CHAMPIONSHIPS 2024": 100121,
	"INTERNAZIONALI BNL D'ITALIA 2024": 100122,
	"MUTUA MADRID OPEN 2024": 100123,
	"PORSCHE TENNIS GRAND PRIX 2024": 100124,
	"ROLEX MONTE-CARLO MASTERS 2024": 100125,
	"BILLIE JEAN KING CUP: USA VS BELGIUM 2024": 100126,
	"MIAMI OPEN PRESENTED BY ITAú 2024": 100127,
	"BNP PARIBAS OPEN 2024": 100128,
	"DUBAI DUTY FREE TENNIS CHAMPIONSHIPS 2024": 100129,
	"QATAR EXXONMOBIL OPEN 2024": 100130,
	"QATAR TOTAL ENERGIES OPEN 2024": 100131,
	"ADELAIDE INTERNATIONAL 2024": 100132,

	"Australian Open 2025": 100133,
	"Roland Garros 2025": 100134,
	"Wimbledon 2025": 100135,
	"US Open 2025": 100136,
	"PRESS CONFERENCES 2025": 100137,
	"BRISBANE INTERNATIONAL 2025": 100138,
	"UNITED CUP 2025": 100139,
	"DAVIS CUP FINALS 2025": 100140,
	"BILLIE JEAN KING CUP 2025": 100141,
	"NITTO ATP FINALS 2025": 100142,
	"ROLEX PARIS MASTERS 2025": 100143,
	"WTA FINALS 2025": 100144,
	"ROLEX SHANGHAI MASTERS 2025": 100145,
	"CHINA OPEN 2025": 100146,
	"LAVER CUP 2025": 100147,
	"NATIONAL BANK OPEN 2025": 100148,
	"OMNIUM BANQUE NATIONALE 2025": 100149,
	"MUBADALA CITI DC OPEN 2025": 100150,
	"INTERNATIONAL TENNIS HALL OF FAME 2025": 100151,
	"THE CHAMPIONSHIPS 2025": 100152,
	"ROTHESAY INTERNATIONAL 2025": 100153,
	"CINCH CHAMPIONSHIPS 2025": 100154,
	"INTERNAZIONALI BNL D'ITALIA 2025": 100155,
	"MUTUA MADRID OPEN 2025": 100156,
	"PORSCHE TENNIS GRAND PRIX 2025": 100157,
	"ROLEX MONTE-CARLO MASTERS 2025": 100158,
	"BILLIE JEAN KING CUP: USA VS BELGIUM 2025": 100159,
	"MIAMI OPEN PRESENTED BY ITAú 2025": 100160,
	"BNP PARIBAS OPEN 2025": 100161,
	"DUBAI DUTY FREE TENNIS CHAMPIONSHIPS 2025": 100162,
	"QATAR EXXONMOBIL OPEN 2025": 100163,
	"QATAR TOTAL ENERGIES OPEN 2025": 100164,
	"ADELAIDE INTERNATIONAL 2025": 100165,

	"Australian Open 2026": 100166,
	"Roland Garros 2026": 100167,
	"Wimbledon 2026": 100168,
	"US Open 2026": 100169,
	"PRESS CONFERENCES 2026": 100170,
	"BRISBANE INTERNATIONAL 2026": 100171,
	"UNITED CUP 2026": 100172,
	"DAVIS CUP FINALS 2026": 100173,
	"BILLIE JEAN KING CUP 2026": 100174,
	"NITTO ATP FINALS 2026": 100175,
	"ROLEX PARIS MASTERS 2026": 100176,
	"WTA FINALS 2026": 100177,
	"ROLEX SHANGHAI MASTERS 2026": 100178,
	"CHINA OPEN 2026": 100179,
	"LAVER CUP 2026": 100180,
	"NATIONAL BANK OPEN 2026": 100181,
	"OMNIUM BANQUE NATIONALE 2026": 100182,
	"MUBADALA CITI DC OPEN 2026": 100183,
	"INTERNATIONAL TENNIS HALL OF FAME 2026": 100184,
	"THE CHAMPIONSHIPS 2026": 100185,
	"ROTHESAY INTERNATIONAL 2026": 100186,
	"CINCH CHAMPIONSHIPS 2026": 100187,
	"INTERNAZIONALI BNL D'ITALIA 2026": 100188,
	"MUTUA MADRID OPEN 2026": 100189,
	"PORSCHE TENNIS GRAND PRIX 2026": 100190,
	"ROLEX MONTE-CARLO MASTERS 2026": 100191,
	"BILLIE JEAN KING CUP: USA VS BELGIUM 2026": 100192,
	"MIAMI OPEN PRESENTED BY ITAú 2026": 100193,
	"BNP PARIBAS OPEN 2026": 100194,
	"DUBAI DUTY FREE TENNIS CHAMPIONSHIPS 2026": 100195,
	"QATAR EXXONMOBIL OPEN 2026": 100196,
	"QATAR TOTAL ENERGIES OPEN 2026": 100197,
	"ADELAIDE INTERNATIONAL 2026": 100198
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


# Player-match linking 

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


#  Main 

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