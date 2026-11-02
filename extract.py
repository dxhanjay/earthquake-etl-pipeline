"""
EXTRACT step — Earthquake ETL Pipeline.

Two modes:

1. Feed mode (default): downloads the USGS "Magnitude 2.5+ Earthquakes,
   Past Week" GeoJSON feed and saves it untouched to data/raw/.

2. Historical mode: pulls ANY past date range from the USGS FDSN event
   API (the same catalogue behind the feed) and saves it to
   data/raw/usgs_history.geojson:

       python extract.py --start 2026-10-01 --end 2026-11-01

   The FDSN API rejects result sets over 20,000 events, so the range is
   requested in <=31-day chunks, merged, de-duplicated by event id and
   sorted by time. Re-running a backfill that overlaps data already in
   the database is safe: the load step upserts on the USGS event id.

The raw layer is never edited by hand or by later steps: if transform /
load logic changes, we re-derive everything from these files.

Standard library only (urllib) — no installs needed for this step.
"""

import argparse
import json
import sys
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

FEED_URL = ("https://earthquake.usgs.gov/earthquakes/feed/v1.0/"
            "summary/2.5_week.geojson")
FDSN_URL = "https://earthquake.usgs.gov/fdsnws/event/1/query"
MIN_MAGNITUDE = 2.5
CHUNK_DAYS = 31  # FDSN caps a response at 20,000 events; a month of
                 # M2.5+ worldwide is far below that, and stays polite.

BASE = Path(__file__).parent
RAW_DIR = BASE / "data" / "raw"
FEED_PATH = RAW_DIR / "usgs_2.5_week.geojson"
HISTORY_PATH = RAW_DIR / "usgs_history.geojson"


def fetch_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "quake-etl/1.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read())


def extract_feed() -> int:
    req = urllib.request.Request(FEED_URL, headers={"User-Agent": "quake-etl/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = resp.read()  # saved byte-for-byte, truly untouched
    data = json.loads(payload)
    features = data.get("features", [])
    if not features:
        print("Feed returned zero features — refusing to overwrite raw data.")
        return 1
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    FEED_PATH.write_bytes(payload)
    generated = datetime.fromtimestamp(
        data["metadata"]["generated"] / 1000, tz=timezone.utc)
    print(f"Feed           : {data['metadata']['title']}")
    print(f"Feed generated : {generated.isoformat()}")
    print(f"Features       : {len(features)}")
    print(f"Saved (raw)    : data/raw/{FEED_PATH.name}")
    return 0


def chunk_ranges(start: date, end: date):
    """Split [start, end] into consecutive <=CHUNK_DAYS windows."""
    cur = start
    while cur < end:
        nxt = min(cur + timedelta(days=CHUNK_DAYS), end)
        yield cur, nxt
        cur = nxt


def extract_history(start: date, end: date) -> int:
    if end <= start:
        print("--end must be after --start.")
        return 1
    by_id: dict[str, dict] = {}
    chunks = list(chunk_ranges(start, end))
    for c_start, c_end in chunks:
        params = {
            "format": "geojson",
            "starttime": c_start.isoformat(),
            "endtime": c_end.isoformat(),
            "minmagnitude": MIN_MAGNITUDE,
            "orderby": "time",
        }
        data = fetch_json(f"{FDSN_URL}?{urllib.parse.urlencode(params)}")
        feats = data.get("features", [])
        for f in feats:
            by_id[f["id"]] = f  # an event revised mid-backfill wins once
        print(f"Chunk {c_start} → {c_end}: {len(feats)} features "
              f"({len(by_id)} unique so far)")
    features = sorted(by_id.values(), key=lambda f: f["properties"]["time"])
    if not features:
        print("Historical query returned zero features — nothing saved.")
        return 1
    payload = {
        "type": "FeatureCollection",
        "metadata": {
            "title": (f"USGS historical query, M{MIN_MAGNITUDE}+, "
                      f"{start.isoformat()} to {end.isoformat()}"),
            "generated": int(datetime.now(timezone.utc).timestamp() * 1000),
            "count": len(features),
        },
        "features": features,
    }
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    HISTORY_PATH.write_text(json.dumps(payload), encoding="utf-8")
    print(f"Range          : {start} → {end} in {len(chunks)} chunk(s)")
    print(f"Features       : {len(features)} (unique by USGS event id)")
    print(f"Saved (raw)    : data/raw/{HISTORY_PATH.name}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="USGS earthquake extract")
    parser.add_argument("--start", type=date.fromisoformat,
                        help="historical mode: first day, YYYY-MM-DD")
    parser.add_argument("--end", type=date.fromisoformat,
                        help="historical mode: day after the last day, YYYY-MM-DD")
    args = parser.parse_args()
    if (args.start is None) != (args.end is None):
        print("Give both --start and --end, or neither (feed mode).")
        return 1
    if args.start:
        return extract_history(args.start, args.end)
    return extract_feed()


if __name__ == "__main__":
    sys.exit(main())
