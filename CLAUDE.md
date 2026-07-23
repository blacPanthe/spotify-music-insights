# Spotify Listening Analytics — Power BI + ML Project

## Goal
Turn raw Spotify Extended Streaming History into an interactive, "hightech" Power BI
dashboard — matching (and exceeding) the scope of a reference LinkedIn project, with
BPM/audio-feature enrichment and an ML layer added on top.

## Source Data
- 17 JSON files in project root: `Streaming_History_Audio_*.json` (music),
  `Streaming_History_Video_*.json` (video, mostly music videos)
- 114,535 total play records, 2019-07-27 to present
- 10,170 unique tracks (by `spotify_track_uri`)
- Key fields: `ts` (UTC), `ms_played`, `platform`, `conn_country`, `ip_addr`,
  `master_metadata_track_name/album_artist_name/album_album_name`,
  `spotify_track_uri`, `reason_start`, `reason_end`, `shuffle`, `skipped`, `offline`
- No genre, no BPM/audio-features, no lyrics in the raw export — must be enriched.
- **Privacy note:** raw files contain `ip_addr` per row. Never commit raw JSON to
  a public repo. Gitignored by default (see below).

## Full Feature Scope (from reference project + additions)

### 1. Album Analysis
- Listening trends over time, year-wise analysis, weekday vs weekend,
  Top 5 Albums, LY vs PY comparison, YoY growth

### 2. Artist Analysis
- Artist listening trends, year-wise artist diversity, weekday vs weekend,
  Top 5 Artists, LY vs PY comparison, YoY growth

### 3. Track Analysis
- Track listening trends, year-wise analysis, Top 5 Tracks, weekday vs weekend,
  LY vs PY comparison, YoY growth

### 4. Listening Pattern Analysis
- Heat map: listening activity by hour x day of week
- Scatter plot with quadrant analysis (engagement patterns)
- Peak listening hours
- Listening duration vs playback frequency

### 5. Interactive Reporting
- Drill-through pages, drill-down hierarchy (Year > Month > Day),
  dynamic filters/slicers, detailed data grid with export

### 6. Audio Feature Enrichment (NEW — added per user request)
- **BPM (tempo)**, valence, energy, danceability per track
- Source: **ReccoBeats API** (confirmed working 2026-07-16 — Spotify's own
  `/audio-features` returns 403 for this app, locked down for new apps since
  Nov 2024). ReccoBeats needs no API key, is free, and mirrors the same fields
  plus extras (acousticness, key, loudness, speechiness, liveness).
  - Step 1: `GET https://api.reccobeats.com/v1/track?ids=<spotify_track_id>` (comma-separated, batchable)
    -> returns ReccoBeats internal track `id`
  - Step 2: `GET https://api.reccobeats.com/v1/track/<reccobeats_id>/audio-features`
    -> returns tempo, valence, energy, danceability, acousticness, key, loudness, speechiness, liveness
- BPM distribution charts, BPM vs listening time, BPM heat map by hour of day

### 7. ML / "Mood" Layer (NEW)
- Mood quadrant (valence x energy) — Happy/Energetic/Calm/Sad
- KMeans clustering on valence + energy + danceability -> mood label per track
- Optional: skip-prediction model (logistic regression / random forest) predicting
  skip probability from BPM/energy/time-of-day/platform, scored back into the model

### Power BI Concepts to Apply
Power Query, data cleaning/transformation, data modeling (star schema),
DAX measures, time intelligence, KPI cards, heat maps, scatter plots,
conditional formatting, drill-through/drill-down, field parameters,
dynamic titles, custom tooltip pages, bookmarks, decomposition tree,
key influencers visual, Q&A visual, smart narrative visual.

## Pipeline

```
[1] RAW DATA (17 JSON files)
        |
[2] INGEST & CLEAN — Python/pandas
    - Merge all JSON, drop empty audiobook cols, convert ts UTC -> local time,
      dedupe unique track URIs
        |
[3] ENRICH — Python + Spotify/ReccoBeats API
    - Pull tempo/valence/energy/danceability for 10,170 unique tracks (~102 batch calls)
        |
[4] STORE — SQLite
    - fact_plays (114,535 rows), dim_tracks (10,170 rows incl. audio features),
      dim_date
        |
[5] ML LAYER — Python/scikit-learn
    - KMeans mood clustering, optional skip-prediction model
    - Write results back into SQLite
        |
[6] POWER BI — connect to SQLite (or Parquet/CSV export)
    - Star schema model, DAX measures, all visuals from feature scope above
        |
[7] PUBLISH — GitHub (.pbip format), README, gitignored raw/private data
```

## Collaboration Model
- **Priority: the Power BI dashboard itself.** This is a data analyst portfolio
  project — DAX fluency, data modeling, and visualization/UX quality are what
  get evaluated, so most effort should go into steps 6-7 below.
- **User builds the dashboard themselves** in Power BI Desktop (data model,
  visuals, formatting, bookmarks, interactivity) — this is the skill being
  demonstrated and stays hands-on.
- **AI's role:** write/run the Python ingestion + enrichment scripts, design
  and write the SQL schema/queries (SQL is being kept deliberately for the
  resume line, even though a pure Power Query path would also work), write
  DAX measures on request, and give implementation guidance/critique as the
  dashboard comes together — not build the report itself.
- Default mode of help going forward: user asks for a specific query/measure
  or "how do I do X in Power BI" / "how can I make Y better" -> AI gives the
  exact DAX/SQL/steps, not a finished visual.

## Timeline
- Solo, no AI help: ~21-33 hours
- With AI writing scripts/DAX/SQL/ML boilerplate: **~8-11 hours**
  (bottleneck is manual Power BI Desktop UI work for visuals/bookmarks — ~3-5 hrs,
  doesn't compress much regardless of AI help)
- Start date: tomorrow

## Status / Next Steps
- [ ] Verify Spotify Developer app has `/audio-features` access (or confirm
      fallback to ReccoBeats API)
- [x] Write ingestion + cleaning script
- [x] Write enrichment script, run against 10,170 unique tracks
      (result: 7,847 enriched / 2,323 not found on ReccoBeats, ~77% match rate —
      misses concentrated in regional/Bollywood catalog)
- [x] Set up SQLite schema, load fact/dim tables
      (dim_date: 2,543 rows, dim_tracks: 7,847 rows, fact_plays: 114,535 rows,
      95,898/114,535 plays matched to an enriched track)
- [ ] ML: mood clustering (+ optional skip-prediction model)
- [ ] Build Power BI model + DAX measures
- [ ] Build visuals per feature scope above
- [ ] Polish (theme, tooltips, bookmarks), write README, push to GitHub as `.pbip`

## Repo Conventions
- Raw data files (`Streaming_History_*.json`, anything with `ip_addr`) are
  gitignored — never commit.
- Power BI project saved in `.pbip` format (not `.pbix`) for readable diffs.
- Enrichment/ML outputs cached locally (e.g. `data/enriched_tracks.parquet`) —
  also gitignored unless scrubbed of any sensitive fields.
