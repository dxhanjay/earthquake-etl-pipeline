# Earthquake ETL Pipeline — USGS Open Data

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)
![Pandas](https://img.shields.io/badge/Pandas-150458?style=flat&logo=pandas&logoColor=white)
![Database](https://img.shields.io/badge/Database-SQLite-003B57?style=flat&logo=sqlite&logoColor=white)
![Status](https://img.shields.io/badge/Status-Complete-brightgreen?style=flat)

A complete, reproducible **ETL pipeline** for live earthquake data: it extracts the USGS *Magnitude 2.5+ Earthquakes, Past Week* GeoJSON feed, cleans it with pandas under explicit data-quality rules, loads it into SQLite with an idempotent upsert design, analyses it with SQL, and renders a self-contained HTML dashboard from the database.

**Live dashboard:** _deployed on Vercel — link added below after deploy_
**Data source:** [USGS Earthquake Catalog feed](https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_week.geojson) (public domain, no API key)

## Pipeline Architecture

```
USGS GeoJSON feed ──extract.py──▶ data/raw/ (untouched JSON)
        ──transform.py (pandas + quality checks)──▶ data/processed/quakes_clean.csv
        ──load.py (SQLite upsert on USGS event id)──▶ data/quakes.db
        ──sql/analysis_queries.sql──▶ findings
        ──build_dashboard.py──▶ site/index.html (live dashboard)
```

## Quick Start

```bash
pip install -r requirements.txt
./run_pipeline.sh        # extract → transform → load → dashboard
```

Or step by step: `python extract.py` → `python transform.py` → `python load.py` → `python build_dashboard.py`. The pipeline is safe to re-run end to end: loads upsert on the USGS event id, so re-runs add zero duplicates — and when USGS revises an event's magnitude or depth, the stored row updates in place.

## Design choices that matter

- **Raw layer is never edited** — every downstream artefact can be rebuilt from `data/raw/`.
- **Cleaning rules are explicit, checks fail loudly** — non-earthquake events removed (the current feed contains 1 *explosion* record), missing magnitudes dropped, duplicates removed by event id, ranges validated (magnitude −2…10, depth −10…750 km) with a non-zero exit on any violation.
- **Idempotent loads** — `id` (USGS event id) is the PRIMARY KEY; `INSERT OR REPLACE` in a single transaction. Verified: second load = **+0 net new**.
- **Derived columns with real-world meaning** — `region` parsed from the place string, `mag_band` on the standard USGS descriptive scale, timestamps in both UTC and IST.
- **The dashboard is generated, not hand-written** — every number on the page comes from a SQL query at build time.

## Findings — Oct 25 – Nov 1, 2026 (332 events)

- **Strongest:** M6.4 southeast of Easter Island (Oct 29, 07:49 UTC, only 10 km deep) — one of just **4 Strong (6.0+)** events all week; the full band split: 141 Minor, 137 Light, 50 Moderate, 4 Strong.
- **Deepest:** M5.5 near Fiji at **642 km** down — deep-focus quakes like this are barely felt at the surface despite their size.
- **Most felt ≠ strongest:** the week's most-reported event was a tiny **M2.73 near Pacifica, California with 520 felt reports** — population density beats magnitude for human impact. 59 of 332 events were felt by someone.
- **Busiest region:** Alaska, with 82 events (a quarter of the planet's M2.5+ week), ahead of Vanuatu (34) and Japan (14).

## Project Structure

```
earthquake-etl-pipeline/
├── extract.py            # USGS GeoJSON feed → data/raw/ (untouched)
├── transform.py          # pandas cleaning + data-quality checks
├── load.py               # SQLite load, idempotent upsert on event id
├── build_dashboard.py    # DB → site/index.html (self-contained dashboard)
├── sql/
│   ├── schema.sql            # earthquakes table + indexes
│   └── analysis_queries.sql  # 8 analysis queries (all executed)
├── site/index.html       # generated dashboard (deployed to Vercel)
├── requirements.txt      # pandas
├── run_pipeline.sh       # one-command end-to-end run
└── data/                 # raw / processed / quakes.db (regenerated, git-ignored)
```

## Skills Demonstrated

Python (REST/GeoJSON APIs, JSON), pandas (flattening nested data, derived columns, deduplication), data cleaning & data-quality engineering, SQL DDL (primary keys, CHECK constraints, indexes), idempotent load design / upserts, SQL analysis (GROUP BY, window functions), automated report/dashboard generation.

## Possible Next Steps

Schedule daily runs (cron/Airflow) so the dashboard tracks a rolling week automatically; add a map view (lat/long are already stored); extend the feed window to 30 days for trend analysis.

## Author

**Dhananjoy Mahato** — final-year BTech CSE, GD Goenka University · [GitHub](https://github.com/dxhanjay) · [LinkedIn](https://www.linkedin.com/in/dhananjoy-mahato-303462272)

## License

MIT — data © U.S. Geological Survey (public domain).
