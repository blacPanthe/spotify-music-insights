"""
Step 4 of pipeline: load cleaned_plays.parquet + enriched_tracks.csv into a
SQLite star schema for Power BI to connect to.

Tables:
  dim_date    - one row per calendar date in the data's range
  dim_tracks  - one row per unique track, incl. audio features + mood label
  fact_plays  - one row per play, FK'd to dim_date/dim_tracks

Output (gitignored, local only): data/spotify_analytics.db
"""
import sqlite3
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "spotify_analytics.db"

PLAYS_PATH = DATA_DIR / "cleaned_plays.parquet"
TRACKS_PATH = DATA_DIR / "enriched_tracks.csv"


def build_dim_date(min_date, max_date) -> pd.DataFrame:
    dates = pd.date_range(min_date, max_date, freq="D")
    df = pd.DataFrame({"date": dates})
    df["date_key"] = df["date"].dt.strftime("%Y%m%d").astype(int)
    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.month
    df["month_name"] = df["date"].dt.month_name()
    df["day"] = df["date"].dt.day
    df["weekday_name"] = df["date"].dt.day_name()
    df["is_weekend"] = df["date"].dt.dayofweek >= 5
    df["week_of_year"] = df["date"].dt.isocalendar().week.astype(int)
    return df


def label_mood(row) -> str:
    v, e = row.get("valence"), row.get("energy")
    if pd.isna(v) or pd.isna(e):
        return "Unknown"
    if v >= 0.5 and e >= 0.5:
        return "Happy/Energetic"
    if v >= 0.5 and e < 0.5:
        return "Calm/Positive"
    if v < 0.5 and e >= 0.5:
        return "Angry/Intense"
    return "Sad/Mellow"


def main():
    plays = pd.read_parquet(PLAYS_PATH)
    plays["date"] = pd.to_datetime(plays["date"])
    plays["date_key"] = plays["date"].dt.strftime("%Y%m%d").astype(int)

    tracks = pd.read_csv(TRACKS_PATH)
    tracks["mood"] = tracks.apply(label_mood, axis=1)
    tracks["track_key"] = range(1, len(tracks) + 1)

    dim_date = build_dim_date(plays["date"].min(), plays["date"].max())

    uri_to_key = dict(zip(tracks["spotify_track_uri"], tracks["track_key"]))
    plays["track_key"] = plays["spotify_track_uri"].map(uri_to_key)

    fact_cols = [
        "track_key", "date_key", "ts", "ts_local", "platform", "conn_country",
        "ms_played", "minutes_played", "hour", "weekday_name", "is_weekend",
        "reason_start", "reason_end", "shuffle", "skipped", "offline",
        "incognito_mode", "content_type", "_source_type",
    ]
    fact_plays = plays[[c for c in fact_cols if c in plays.columns]].copy()
    fact_plays["play_id"] = range(1, len(fact_plays) + 1)

    dim_tracks_cols = [
        "track_key", "spotify_track_uri", "track_name", "artist_name",
        "album_name", "play_count", "total_minutes", "tempo", "valence",
        "energy", "danceability", "acousticness", "instrumentalness",
        "liveness", "loudness", "speechiness", "key", "mode", "mood",
    ]
    dim_tracks = tracks[[c for c in dim_tracks_cols if c in tracks.columns]].copy()

    with sqlite3.connect(DB_PATH) as conn:
        dim_date.to_sql("dim_date", conn, if_exists="replace", index=False)
        dim_tracks.to_sql("dim_tracks", conn, if_exists="replace", index=False)
        fact_plays.to_sql("fact_plays", conn, if_exists="replace", index=False)

        conn.execute("CREATE INDEX IF NOT EXISTS idx_fact_track ON fact_plays(track_key)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_fact_date ON fact_plays(date_key)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_dim_date_key ON dim_date(date_key)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_dim_tracks_key ON dim_tracks(track_key)")

    print(f"Built {DB_PATH}")
    print(f"  dim_date:   {len(dim_date):,} rows")
    print(f"  dim_tracks: {len(dim_tracks):,} rows")
    print(f"  fact_plays: {len(fact_plays):,} rows")
    matched = fact_plays["track_key"].notna().sum()
    print(f"  fact_plays matched to dim_tracks: {matched:,}/{len(fact_plays):,}")


if __name__ == "__main__":
    main()
