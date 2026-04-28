"""
PART 4 — Feature Engineering
==============================
Builds the final modelling DataFrame by:

  1. Computing the Cumulative Tournament Fatigue Index (CTFI)
     using SQL window functions (cumulative sets/hours played
     per player per tournament, before the current match).

  2. Engineering rank-based features.

  3. Joining match data ← → NLP transcript features.

  4. Exporting the final feature matrix to `features.csv`.

Install dependencies:
    pip install pandas numpy sqlite3  (all standard / already installed)

Usage:
    python part4_features.py
"""

import sqlite3
import numpy as np
import pandas as pd

DB_PATH       = "tennis_upsets.db"
FEATURES_OUT  = "features.csv"


# ── Helpers ───────────────────────────────────────────────────────────────────

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


# ── Step 1: Load Grand Slam matches ──────────────────────────────────────────

def load_matches() -> pd.DataFrame:
    """
    Pull all Grand Slam matches from the DB.
    We reshape into a player-centric format:
      one row per player per match  (so each match yields 2 rows).
    """
    conn = get_connection()

    matches = pd.read_sql("""
        SELECT
            rowid                           AS match_db_id,
            tourney_id,
            tourney_name,
            slam_name,
            tourney_date,
            match_num,
            round,
            surface,
            best_of,
            winner_id                       AS player_id,
            winner_name                     AS player_name,
            winner_rank                     AS rank,
            winner_rank_points              AS rank_points,
            loser_id                        AS opponent_id,
            loser_name                      AS opponent_name,
            loser_rank                      AS opp_rank,
            loser_rank_points               AS opp_rank_points,
            score,
            upset,
            rank_diff,
            1                               AS won_match  -- winner's perspective
        FROM matches

        UNION ALL

        SELECT
            rowid,
            tourney_id, tourney_name, slam_name, tourney_date, match_num,
            round, surface, best_of,
            loser_id,  loser_name,  loser_rank,  loser_rank_points,
            winner_id, winner_name, winner_rank, winner_rank_points,
            score,
            upset,
            -rank_diff,
            0                               AS won_match  -- loser's perspective
        FROM matches

        ORDER BY tourney_date, tourney_id, match_num
    """, conn)

    conn.close()

    matches["tourney_date"] = pd.to_datetime(matches["tourney_date"], errors="coerce")
    matches["rank"]         = pd.to_numeric(matches["rank"],     errors="coerce")
    matches["opp_rank"]     = pd.to_numeric(matches["opp_rank"], errors="coerce")

    print(f"Player-match rows loaded: {len(matches):,}")
    return matches


# ── Step 2: Parse score into sets/games ──────────────────────────────────────

def parse_score(score: str) -> dict:
    """
    Parse a score string like '6-3 4-6 7-6(4) 6-2' into:
      sets_played, total_games, sets_won, sets_lost
    for the winner.  (We'll compute loser perspective separately.)
    """
    if not isinstance(score, str) or not score.strip():
        return {"sets_played": 3, "total_games": 30, "sets_won": 2, "sets_lost": 1}

    sets = re.findall(r"(\d+)-(\d+)", score)
    if not sets:
        return {"sets_played": 3, "total_games": 30, "sets_won": 2, "sets_lost": 1}

    sets_played = len(sets)
    sets_won    = sum(1 for w, l in sets if int(w) > int(l))
    sets_lost   = sets_played - sets_won
    total_games = sum(int(w) + int(l) for w, l in sets)

    return {
        "sets_played":  sets_played,
        "total_games":  total_games,
        "sets_won":     sets_won,
        "sets_lost":    sets_lost,
    }


import re


def enrich_score_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add sets_played, total_games, sets_won, sets_lost columns."""
    parsed = df["score"].apply(parse_score).apply(pd.Series)
    df     = pd.concat([df, parsed], axis=1)

    # From winner's perspective the sets_won/lost are already correct.
    # For loser rows (won_match==0) we swap won ↔ lost.
    loser_mask        = df["won_match"] == 0
    df.loc[loser_mask, ["sets_won", "sets_lost"]] = (
        df.loc[loser_mask, ["sets_lost", "sets_won"]].values
    )
    return df


# ── Step 3: Cumulative Tournament Fatigue Index (CTFI) ──────────────────────
#
#  CTFI for player P before match M in tournament T =
#    Σ sets_played  (all of P's earlier matches in T, i.e. match_num < M)
#
#  We compute this with a SQL window function for correctness and speed.
#  The intuition: a player who has gone to 5 sets twice before their
#  QF has a much higher fatigue load than someone who won in straight sets.

CTFI_QUERY = """
WITH player_match_sets AS (
    -- Sets played by each player in each tournament match (winner side)
    SELECT
        tourney_id,
        match_num,
        winner_id  AS player_id,
        (LENGTH(score) - LENGTH(REPLACE(score, '-', ''))) / 2  AS approx_sets,
        CAST(SUBSTR(tourney_date, 1, 8) AS INTEGER)            AS match_date_int
    FROM matches

    UNION ALL

    -- Loser side (same sets_played)
    SELECT
        tourney_id,
        match_num,
        loser_id,
        (LENGTH(score) - LENGTH(REPLACE(score, '-', ''))) / 2,
        CAST(SUBSTR(tourney_date, 1, 8) AS INTEGER)
    FROM matches
),
ctfi_raw AS (
    SELECT
        tourney_id,
        player_id,
        match_num,
        approx_sets,
        match_date_int,
        -- Cumulative sum of sets BEFORE this match (EXCLUDE current)
        SUM(approx_sets) OVER (
            PARTITION BY player_id, tourney_id
            ORDER BY match_num
            ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
        ) AS ctfi
    FROM player_match_sets
)
SELECT
    tourney_id,
    player_id,
    match_num,
    COALESCE(ctfi, 0) AS ctfi
FROM ctfi_raw
"""


def compute_ctfi() -> pd.DataFrame:
    """Run the CTFI window-function query and return a lookup DataFrame."""
    conn  = get_connection()
    ctfi  = pd.read_sql(CTFI_QUERY, conn)
    conn.close()
    print(f"CTFI rows computed: {len(ctfi):,}")
    return ctfi


# ── Step 4: Rank-based features ───────────────────────────────────────────────

def add_rank_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Derived rank features:
      rank_ratio       : player_rank / opp_rank  (>1 = underdog)
      log_rank_diff    : log(|rank_diff| + 1) * sign(rank_diff)
      is_underdog      : 1 if player_rank > opp_rank
      rank_bin         : bucket for player's seeding (top10, 10-30, 30-100, 100+)
    """
    df = df.copy()

    df["rank_ratio"]    = df["rank"] / df["opp_rank"].replace(0, np.nan)
    df["log_rank_diff"] = np.sign(df["rank_diff"]) * np.log1p(np.abs(df["rank_diff"]))
    df["is_underdog"]   = (df["rank"] > df["opp_rank"]).astype(int)

    df["rank_bin"] = pd.cut(
        df["rank"],
        bins=[0, 10, 30, 100, np.inf],
        labels=["top10", "top30", "top100", "outside100"],
        right=True,
    )

    # Round encoding (ordinal)
    round_order = {"R1": 1, "R2": 2, "R3": 3, "R4": 4, "QF": 5, "SF": 6, "F": 7}
    df["round_num"] = df["round"].map(round_order).fillna(3)

    return df


# ── Step 5: Surface encoding ──────────────────────────────────────────────────

def encode_surface(df: pd.DataFrame) -> pd.DataFrame:
    surface_dummies = pd.get_dummies(df["surface"], prefix="surface", dtype=int)
    return pd.concat([df, surface_dummies], axis=1)


# ── Step 6: Merge transcript NLP features ────────────────────────────────────

def load_transcript_features() -> pd.DataFrame:
    """
    Load NLP features from the transcripts table.
    One row per player per tournament round.
    We take the MOST RECENT transcript before each match.
    """
    conn = get_connection()

    # Check that NLP columns exist
    cols_info = conn.execute("PRAGMA table_info(transcripts)").fetchall()
    col_names = {row[1] for row in cols_info}

    if "sentiment_polarity" not in col_names:
        conn.close()
        print("[WARN] NLP columns not found — run part3_nlp.py first.")
        return pd.DataFrame()

    transcript_df = pd.read_sql("""
        SELECT
            player_id,
            player_name,
            tourney_name,
            tourney_date,
            round,
            sentiment_label,
            sentiment_polarity,
            fatigue_total,
            fatigue_word_density,
            fatigue_physical,
            fatigue_mental,
            fatigue_schedule,
            fatigue_injury,
            fatigue_motivation,
            avg_sentence_len,
            type_token_ratio,
            first_person_rate,
            negation_rate,
            word_count,
            llm_fatigue_label,
            llm_fatigue_confidence
        FROM transcripts
        WHERE nlp_processed = 1
    """, conn)
    conn.close()

    # Binary encode LLM label
    if "llm_fatigue_label" in transcript_df.columns:
        transcript_df["llm_is_fatigued"] = (
            transcript_df["llm_fatigue_label"] == "FATIGUED"
        ).astype(float)
        transcript_df["llm_is_fatigued"].fillna(0.5, inplace=True)

    print(f"Transcript NLP rows loaded: {len(transcript_df):,}")
    return transcript_df


def merge_transcripts(matches: pd.DataFrame, transcripts: pd.DataFrame) -> pd.DataFrame:
    """
    Left-join transcripts onto matches.
    Match key: player_id + tourney_name + round (approximate).
    Missing transcripts → NaN (handled by imputation in Part 5).
    """
    if transcripts.empty:
        print("[INFO] No transcript data — NLP columns will be NaN.")
        return matches

    nlp_cols = [
        "sentiment_polarity", "fatigue_total", "fatigue_word_density",
        "fatigue_physical", "fatigue_mental", "fatigue_schedule",
        "fatigue_injury", "fatigue_motivation",
        "avg_sentence_len", "type_token_ratio",
        "first_person_rate", "negation_rate", "word_count",
        "llm_is_fatigued",
    ]
    available = [c for c in nlp_cols if c in transcripts.columns]

    trans_subset = transcripts[["player_id", "tourney_name", "round"] + available].copy()

    # Standardise round labels for joining
    round_map = {
        "first round": "R1", "second round": "R2", "third round": "R3",
        "fourth round": "R4", "quarterfinal": "QF", "semifinal": "SF",
        "final": "F", "r1": "R1", "r2": "R2", "r3": "R3", "r4": "R4",
    }
    trans_subset["round"] = (
        trans_subset["round"].str.lower().map(round_map).fillna(trans_subset["round"])
    )

    merged = matches.merge(
        trans_subset,
        on=["player_id", "tourney_name", "round"],
        how="left",
        suffixes=("", "_transcript"),
    )

    n_matched = merged[available[0]].notna().sum() if available else 0
    print(f"Transcript features matched: {n_matched:,}/{len(merged):,} rows")
    return merged


# ── Step 7: Final assembly ────────────────────────────────────────────────────

FEATURE_COLS = [
    # Match context
    "slam_name", "surface", "round_num", "best_of",
    # Rank features
    "rank", "opp_rank", "rank_ratio", "log_rank_diff",
    "is_underdog", "rank_bin",
    # Fatigue index
    "ctfi",
    # Surface dummies (added dynamically)
    # NLP features (may be NaN for unmatched rows)
    "sentiment_polarity", "fatigue_total", "fatigue_word_density",
    "fatigue_physical", "fatigue_mental", "fatigue_schedule",
    "fatigue_injury", "fatigue_motivation",
    "first_person_rate", "negation_rate",
    "llm_is_fatigued",
    # Target
    "upset",
]


def build_final_features(
    matches: pd.DataFrame,
    ctfi:    pd.DataFrame,
    transcripts: pd.DataFrame,
) -> pd.DataFrame:
    """Full pipeline: enrich → merge CTFI → merge NLP → select features."""

    # 1. Score features
    df = enrich_score_features(matches)

    # 2. Rank features
    df = add_rank_features(df)

    # 3. Surface encoding
    df = encode_surface(df)

    # 4. Merge CTFI
    df = df.merge(
        ctfi[["tourney_id", "player_id", "match_num", "ctfi"]],
        on=["tourney_id", "player_id", "match_num"],
        how="left",
    )
    df["ctfi"] = df["ctfi"].fillna(0)

    # 5. Merge transcript NLP features
    df = merge_transcripts(df, transcripts)

    # 6. Subset to feature columns (add surface dummies)
    surface_dummies = [c for c in df.columns if c.startswith("surface_")]
    keep_cols       = [c for c in FEATURE_COLS + surface_dummies if c in df.columns]
    df_features     = df[keep_cols].copy()

    # 7. Drop rows where target is missing
    df_features = df_features.dropna(subset=["upset"])

    return df_features


# ── Step 8: Descriptive statistics ───────────────────────────────────────────

def describe_features(df: pd.DataFrame) -> None:
    """Print a compact feature summary."""
    print("\n── Feature matrix summary ────────────────────────")
    print(f"  Rows     : {len(df):,}")
    print(f"  Columns  : {len(df.columns)}")
    print(f"  Upset rate: {df['upset'].mean()*100:.1f}%")
    print("\n  Numeric feature stats:")
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    if "upset" in numeric_cols:
        numeric_cols.remove("upset")
    print(df[numeric_cols].describe().round(3).to_string())
    print("\n  Missing values:")
    missing = df.isnull().mean()
    missing = missing[missing > 0].round(3)
    print(missing.to_string() if not missing.empty else "    None")
    print("──────────────────────────────────────────────────\n")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 60)
    print("  PART 4 — Feature Engineering")
    print("=" * 60)

    matches     = load_matches()
    ctfi        = compute_ctfi()
    transcripts = load_transcript_features()

    df_features = build_final_features(matches, ctfi, transcripts)
    describe_features(df_features)

    df_features.to_csv(FEATURES_OUT, index=False)
    print(f"Feature matrix exported to: {FEATURES_OUT}")
    print("\nPart 4 complete. Run part5_model.py next.")


if __name__ == "__main__":
    main()