"""
EXTRACT step — Earthquake ETL Pipeline.

Downloads the USGS "Magnitude 2.5+ Earthquakes, Past Week" GeoJSON feed
and saves it untouched to data/raw/. The raw layer is never edited by
hand or by later steps: if transform/load logic changes, we re-derive
everything from this file.

Standard library only (urllib) — no installs needed for this step.

Run:  python extract.py
"""

import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

FEED_URL = ("https://earthquake.usgs.gov/earthquakes/feed/v1.0/"
            "summary/2.5_week.geojson")
BASE = Path(__file__).parent
RAW_PATH = BASE / "data" / "raw" / "usgs_2.5_week.geojson"


def main() -> int:
    RAW_PATH.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(FEED_URL, headers={"User-Agent": "quake-etl/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = resp.read()

    data = json.loads(payload)
    features = data.get("features", [])
    if not features:
        print("Feed returned zero features — refusing to overwrite raw data.")
        return 1

    RAW_PATH.write_bytes(payload)
    generated = datetime.fromtimestamp(
        data["metadata"]["generated"] / 1000, tz=timezone.utc)
    print(f"Feed           : {data['metadata']['title']}")
    print(f"Feed generated : {generated.isoformat()}")
    print(f"Features       : {len(features)}")
    print(f"Saved (raw)    : data/raw/{RAW_PATH.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
