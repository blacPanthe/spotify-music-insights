"""
Step 2 of pipeline: merge all Streaming_History_*.json files, clean, and
produce (a) a cleaned plays table and (b) the list of unique tracks that
need audio-feature enrichment.

Outputs (gitignored, local only):
  data/cleaned_plays.parquet   - one row per play, cleaned + derived columns
  data/unique_tracks.csv       - one row per unique spotify_track_uri
"""
import glob
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

# Country -> IANA timezone. Extend if your export has more countries with
# meaningful volume; everything else falls back to UTC.
COUNTRY_TZ = {
    "IN": "Asia/Kolkata",
    "US": "America/New_York",
    "GB": "Europe/London",
    "CA": "America/Toronto",
    "NL": "Europe/Amsterdam",
    "FR": "Europe/Paris",
    "CZ": "Europe/Prague",
    "JP": "Asia/Tokyo",
    "DE": "Europe/Berlin",
    "ES": "Europe/Madrid",
    "RO": "Europe/Bucharest",
    "SA": "Asia/Riyadh",
}


def load_all_records():
    records = []
    for fname in sorted(glob.glob(str(ROOT / "Streaming_History_*.json"))):
        source = "video" if "_Video_" in fname else "audio"
        with open(fname, encoding="utf-8") as f:
            data = json.load(f)
        for rec in data:
            rec["_source_file"] = Path(fname).name
            rec["_source_type"] = source
            records.append(rec)
    return records


def clean(df: pd.DataFrame) -> pd.DataFrame:
    # Drop audiobook columns - 0% populated in this export
    audiobook_cols = [
        "audiobook_title",
        "audiobook_uri",
        "audiobook_chapter_uri",
        "audiobook_chapter_title",
    ]
    df = df.drop(columns=[c for c in audiobook_cols if c in df.columns])

    df["ts"] = pd.to_datetime(df["ts"], utc=True)

    # Localize per-row using conn_country -> timezone map, fallback UTC
    def to_local(row):
        tz = COUNTRY_TZ.get(row["conn_country"])
        ts = row["ts"].tz_convert(tz) if tz else row["ts"]
        return ts.tz_localize(None)

    df["ts_local"] = pd.to_datetime(df.apply(to_local, axis=1))

    df["date"] = df["ts_local"].dt.date
    df["year"] = df["ts_local"].dt.year
    df["month"] = df["ts_local"].dt.month
    df["hour"] = df["ts_local"].dt.hour
    df["weekday_name"] = df["ts_local"].dt.day_name()
    df["is_weekend"] = df["ts_local"].dt.dayofweek >= 5

    df["minutes_played"] = df["ms_played"] / 60000

    df["content_type"] = df["episode_name"].notna().map(
        {True: "Podcast", False: "Music"}
    )

    df = df.rename(
        columns={
            "master_metadata_track_name": "track_name",
            "master_metadata_album_artist_name": "artist_name",
            "master_metadata_album_album_name": "album_name",
        }
    )

    return df


def main():
    print("Loading JSON files...")
    records = load_all_records()
    df = pd.DataFrame(records)
    print(f"Loaded {len(df):,} raw records")

    df = clean(df)

    out_path = DATA_DIR / "cleaned_plays.parquet"
    df.to_parquet(out_path, index=False)
    print(f"Wrote cleaned plays -> {out_path} ({len(df):,} rows)")

    music = df[df["spotify_track_uri"].notna()]
    unique_tracks = (
        music.groupby("spotify_track_uri")
        .agg(
            track_name=("track_name", "first"),
            artist_name=("artist_name", "first"),
            album_name=("album_name", "first"),
            play_count=("spotify_track_uri", "count"),
            total_minutes=("minutes_played", "sum"),
        )
        .reset_index()
        .sort_values("play_count", ascending=False)
    )

    tracks_path = DATA_DIR / "unique_tracks.csv"
    unique_tracks.to_csv(tracks_path, index=False)
    print(f"Wrote {len(unique_tracks):,} unique tracks -> {tracks_path}")


if __name__ == "__main__":
    main()
