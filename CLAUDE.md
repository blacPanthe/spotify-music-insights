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
- Source: Spotify `/audio-features` API if dev app has access (locked down for
  new apps since Nov 2024 — verify first), fallback: ReccoBeats API
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

## Timeline
- Solo, no AI help: ~21-33 hours
- With AI writing scripts/DAX/SQL/ML boilerplate: **~8-11 hours**
  (bottleneck is manual Power BI Desktop UI work for visuals/bookmarks — ~3-5 hrs,
  doesn't compress much regardless of AI help)
- Start date: tomorrow

## Status / Next Steps
- [ ] Verify Spotify Developer app has `/audio-features` access (or confirm
      fallback to ReccoBeats API)
- [ ] Write ingestion + cleaning script
- [ ] Write enrichment script, run against 10,170 unique tracks
- [ ] Set up SQLite schema, load fact/dim tables
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
