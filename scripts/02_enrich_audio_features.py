"""
Step 3 of pipeline: enrich unique_tracks.csv with audio features
(tempo/BPM, valence, energy, danceability, etc.) via the ReccoBeats API.

No API key needed. Two calls per track:
  1. GET /v1/track?ids=<spotify_id>        -> resolve ReccoBeats internal id
  2. GET /v1/track/<id>/audio-features     -> get the actual features

Caches progress to disk so the script can be safely re-run/resumed if it
gets interrupted (e.g. network hiccup).

Output (gitignored, local only): data/enriched_tracks.csv
"""
import time
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
IN_PATH = DATA_DIR / "unique_tracks.csv"
OUT_PATH = DATA_DIR / "enriched_tracks.csv"

BASE_URL = "https://api.reccobeats.com/v1"
BATCH_SIZE = 40          # tracks per /v1/track lookup call
SLEEP_BETWEEN_CALLS = 0.1  # be polite to the free API

FEATURE_COLS = [
    "acousticness", "danceability", "energy", "instrumentalness",
    "key", "liveness", "loudness", "mode", "speechiness", "tempo", "valence",
]


def spotify_id_from_uri(uri: str) -> str:
    return uri.split(":")[-1]


def resolve_reccobeats_ids(spotify_ids: list[str]) -> dict:
    """spotify_track_id -> reccobeats_internal_id"""
    ids_param = ",".join(spotify_ids)
    resp = requests.get(f"{BASE_URL}/track", params={"ids": ids_param}, timeout=30)
    if resp.status_code != 200:
        print(f"  batch lookup failed ({resp.status_code}): {resp.text[:200]}")
        return {}
    mapping = {}
    for item in resp.json().get("content", []):
        href = item.get("href", "")
        sp_id = href.rstrip("/").split("/")[-1] if href else None
        if sp_id:
            mapping[sp_id] = item["id"]
    return mapping


def fetch_audio_features(reccobeats_id: str) -> dict | None:
    resp = requests.get(f"{BASE_URL}/track/{reccobeats_id}/audio-features", timeout=30)
    if resp.status_code != 200:
        return None
    return resp.json()


def main():
    tracks = pd.read_csv(IN_PATH)
    tracks["spotify_id"] = tracks["spotify_track_uri"].apply(spotify_id_from_uri)

    # Resume support: skip tracks already enriched in a previous run
    done_ids = set()
    if OUT_PATH.exists():
        existing = pd.read_csv(OUT_PATH)
        done_ids = set(existing["spotify_track_uri"])
        print(f"Resuming - {len(done_ids):,} tracks already enriched.")
    else:
        existing = pd.DataFrame()

    todo = tracks[~tracks["spotify_track_uri"].isin(done_ids)].reset_index(drop=True)
    print(f"{len(todo):,} tracks left to enrich.")

    results = []
    not_found = []

    for batch_start in range(0, len(todo), BATCH_SIZE):
        batch = todo.iloc[batch_start:batch_start + BATCH_SIZE]
        id_map = resolve_reccobeats_ids(batch["spotify_id"].tolist())
        time.sleep(SLEEP_BETWEEN_CALLS)

        for _, row in batch.iterrows():
            rb_id = id_map.get(row["spotify_id"])
            if not rb_id:
                not_found.append(row["spotify_track_uri"])
                continue
            feats = fetch_audio_features(rb_id)
            time.sleep(SLEEP_BETWEEN_CALLS)
            if not feats:
                not_found.append(row["spotify_track_uri"])
                continue
            record = row.to_dict()
            for col in FEATURE_COLS:
                record[col] = feats.get(col)
            results.append(record)

        done_so_far = batch_start + len(batch)
        print(f"  {done_so_far:,}/{len(todo):,} processed "
              f"({len(results):,} enriched, {len(not_found):,} not found)")

        # checkpoint every batch so a crash doesn't lose progress
        if results:
            new_df = pd.DataFrame(results)
            combined = pd.concat([existing, new_df], ignore_index=True) if len(existing) else new_df
            combined.to_csv(OUT_PATH, index=False)

    print(f"\nDone. Enriched: {len(results) + len(existing):,}, "
          f"not found on ReccoBeats: {len(not_found):,}")
    if not_found:
        nf_path = DATA_DIR / "not_found_tracks.csv"
        pd.Series(not_found, name="spotify_track_uri").to_csv(nf_path, index=False)
        print(f"Wrote not-found list -> {nf_path}")


if __name__ == "__main__":
    main()
