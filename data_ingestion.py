"""
PART 1 — Data Ingestion
=======================
Downloads Jeff Sackmann's tennis_atp repository CSVs (match results +
rankings) and loads them into a local SQLite database.

Install dependencies:
    pip install pandas requests tqdm

Usage:
    python part1_data_ingestion.py
"""

import os
import io
import sqlite3
import requests
import pandas as pd
from tqdm import tqdm

# ── Config ────────────────────────────────────────────────────────────────────

DB_PATH = "tennis_upsets.db"

# Jeff Sackmann's open-source ATP data on GitHub
BASE_URL = "https://raw.githubusercontent.com/JeffSackmann/tennis_atp/master"

# Grand Slam tournaments we care about
GRAND_SLAM_IDS = {
    "520": "Australian Open",
    "540": "Roland Garros",
    "560": "Wimbledon",
    "580": "US Open",
}

# Years to collect (adjust as needed)
YEARS = list(range(2015, 2025))


# ── Helpers ───────────────────────────────────────────────────────────────────

def fetch_csv(url: str) -> pd.DataFrame | None:
    """Download a CSV from a URL and return a DataFrame, or None on failure."""
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        return pd.read_csv(io.StringIO(resp.text), low_memory=False)
    except Exception as exc:
        print(f"  [WARN] Could not fetch {url}: {exc}")
        return None


def get_connection() -> sqlite3.Connection:
    """Return a sqlite3 connection with WAL mode for better concurrency."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


# ── Step 1: Download match data ───────────────────────────────────────────────

def download_matches(years: list[int]) -> pd.DataFrame:
    """
    Download atp_matches_YYYY.csv for each year and concatenate.
    Each row is one match with winner/loser ranks, scores, tournament info, etc.
    """
    frames = []
    for year in tqdm(years, desc="Downloading match CSVs"):
        url = f"{BASE_URL}/atp_matches_{year}.csv"
        df = fetch_csv(url)
        if df is not None:
            df["year"] = year
            frames.append(df)

    if not frames:
        raise RuntimeError("No match data could be downloaded.")

    matches = pd.concat(frames, ignore_index=True)
    print(f"\nTotal matches downloaded: {len(matches):,}")
    return matches


# ── Step 2: Filter Grand Slams and clean ─────────────────────────────────────

def filter_grand_slams(matches: pd.DataFrame) -> pd.DataFrame:
    """
    Keep only Grand Slam main-draw matches.
    Columns we need:
      tourney_id, tourney_name, tourney_date, match_num,
      winner_id, winner_name, winner_rank, winner_ioc,
      loser_id,  loser_name,  loser_rank,  loser_ioc,
      score, best_of, round, surface
    """
    # tourney_id format: "YYYY-NNNN"; we match on the 4-digit suffix
    slam_suffixes = set(GRAND_SLAM_IDS.keys())
    mask = matches["tourney_id"].astype(str).str[-3:].isin(slam_suffixes) | \
           matches["tourney_id"].astype(str).str.split("-").str[-1].isin(slam_suffixes)

    slams = matches[mask].copy()
    print(f"Grand Slam matches found: {len(slams):,}")

    # Coerce rank columns to numeric (missing → NaN, not crash)
    for col in ["winner_rank", "loser_rank"]:
        slams[col] = pd.to_numeric(slams[col], errors="coerce")

    # Drop rows where we can't determine who was favourite
    slams = slams.dropna(subset=["winner_rank", "loser_rank"])

    # Create upset label:
    #   upset = 1  if  winner_rank > loser_rank  (lower-ranked player won)
    #   upset = 0  otherwise
    slams["upset"] = (slams["winner_rank"] > slams["loser_rank"]).astype(int)

    # Rank differential (positive = winner was underdog by this many places)
    slams["rank_diff"] = slams["winner_rank"] - slams["loser_rank"]

    # Normalise tourney_date to YYYY-MM-DD
    slams["tourney_date"] = pd.to_datetime(
        slams["tourney_date"].astype(str), format="%Y%m%d", errors="coerce"
    )

    # Add a clean slam name column
    slams["slam_name"] = slams["tourney_id"].astype(str).str.split("-").str[-1].map(
        GRAND_SLAM_IDS
    )

    return slams


# ── Step 3: Download rankings ─────────────────────────────────────────────────

def download_rankings(years: list[int]) -> pd.DataFrame:
    """
    Download weekly ranking snapshots.
    Returns columns: ranking_date, rank, player_id, points
    """
    frames = []
    # Rankings files come in decades
    decades = sorted({(y // 10) * 10 for y in years})
    for decade in tqdm(decades, desc="Downloading ranking CSVs"):
        url = f"{BASE_URL}/atp_rankings_{decade}s.csv"
        df = fetch_csv(url)
        if df is not None:
            frames.append(df)

    if not frames:
        print("[WARN] No ranking data downloaded — continuing without it.")
        return pd.DataFrame()

    rankings = pd.concat(frames, ignore_index=True)
    rankings.columns = ["ranking_date", "rank", "player_id", "points"]
    rankings["ranking_date"] = pd.to_datetime(
        rankings["ranking_date"].astype(str), format="%Y%m%d", errors="coerce"
    )
    print(f"Ranking rows downloaded: {len(rankings):,}")
    return rankings


# ── Step 4: Download player info ──────────────────────────────────────────────

def download_players() -> pd.DataFrame:
    """Download master player table (id, name, hand, DOB, IOC)."""
    url = f"{BASE_URL}/atp_players.csv"
    df = fetch_csv(url)
    if df is None:
        return pd.DataFrame()

    df.columns = ["player_id", "first_name", "last_name", "hand", "dob", "ioc", "height", "wikidata_id"]
    df["full_name"] = df["first_name"].fillna("") + " " + df["last_name"].fillna("")
    df["full_name"] = df["full_name"].str.strip()
    df["dob"] = pd.to_datetime(df["dob"].astype(str), format="%Y%m%d", errors="coerce")
    print(f"Players loaded: {len(df):,}")
    return df


# ── Step 5: Write to SQLite ───────────────────────────────────────────────────

def write_to_db(
    matches: pd.DataFrame,
    rankings: pd.DataFrame,
    players: pd.DataFrame,
) -> None:
    """Write all three tables to SQLite. Replace existing data."""
    conn = get_connection()

    print("\nWriting matches …")
    matches.to_sql("matches", conn, if_exists="replace", index=False)

    if not rankings.empty:
        print("Writing rankings …")
        rankings.to_sql("rankings", conn, if_exists="replace", index=False)

    if not players.empty:
        print("Writing players …")
        players.to_sql("players", conn, if_exists="replace", index=False)

    # Create useful indexes
    conn.execute("CREATE INDEX IF NOT EXISTS idx_matches_winner ON matches(winner_id);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_matches_loser  ON matches(loser_id);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_matches_date   ON matches(tourney_date);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_rankings_player ON rankings(player_id);")
    conn.commit()
    conn.close()
    print(f"\nDatabase written to: {os.path.abspath(DB_PATH)}")


# ── Step 6: Quick sanity check ────────────────────────────────────────────────

def sanity_check() -> None:
    """Print a few summary stats to confirm data looks right."""
    conn = get_connection()

    total = conn.execute("SELECT COUNT(*) FROM matches").fetchone()[0]
    upsets = conn.execute("SELECT COUNT(*) FROM matches WHERE upset=1").fetchone()[0]
    slams  = conn.execute(
        "SELECT slam_name, COUNT(*) as n FROM matches GROUP BY slam_name ORDER BY n DESC"
    ).fetchall()

    print("\n── Sanity check ──────────────────────────────")
    print(f"  Total Grand Slam matches : {total:,}")
    print(f"  Upset matches            : {upsets:,}  ({upsets/total*100:.1f}%)")
    print("  Breakdown by slam:")
    for name, n in slams:
        print(f"    {name or 'Unknown':<20} {n:>5,}")
    print("─────────────────────────────────────────────\n")
    conn.close()


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 60)
    print("  PART 1 — Tennis Data Ingestion")
    print("=" * 60)

    raw_matches  = download_matches(YEARS)
    slam_matches = filter_grand_slams(raw_matches)
    rankings     = download_rankings(YEARS)
    players      = download_players()

    write_to_db(slam_matches, rankings, players)
    sanity_check()

    print("Part 1 complete. Run part2_scraping.py next.")


if __name__ == "__main__":
    main()