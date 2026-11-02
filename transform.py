"""
TRANSFORM step — Earthquake ETL Pipeline.

Reads the raw USGS GeoJSON (data/raw/usgs_2.5_week.geojson), flattens it
into a tidy table with pandas, derives analysis-friendly columns, and
runs explicit data-quality checks. Any check failure exits non-zero —
pipelines should fail loudly, never clean silently.

Derived columns:
  occurred_at_utc / occurred_at_ist — epoch ms converted to timestamps
  region       — text after the last comma in `place` (e.g. "Hawaii"),
                 falling back to the full place string
  mag_band     — Minor (2.5-3.9) / Light (4.0-4.9) / Moderate (5.0-5.9) /
                 Strong (6.0+), the standard USGS descriptive scale
  depth_km     — from the GeoJSON geometry (coordinates[2])

Output: data/processed/quakes_clean.csv

Run:  python transform.py   (after extract.py)
      python transform.py --raw data/raw/usgs_history.geojson
          (after a historical extract — same cleaning rules apply)
"""

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

BASE = Path(__file__).parent
RAW_PATH = BASE / "data" / "raw" / "usgs_2.5_week.geojson"
OUT_PATH = BASE / "data" / "processed" / "quakes_clean.csv"


def mag_band(mag: float) -> str:
    if mag < 4.0:
        return "Minor (2.5-3.9)"
    if mag < 5.0:
        return "Light (4.0-4.9)"
    if mag < 6.0:
        return "Moderate (5.0-5.9)"
    return "Strong (6.0+)"


def main() -> int:
    parser = argparse.ArgumentParser(description="Clean a raw USGS extract")
    parser.add_argument("--raw", type=Path, default=RAW_PATH,
                        help="raw GeoJSON to clean (default: the weekly feed)")
    args = parser.parse_args()
    raw_path = args.raw if args.raw.is_absolute() else BASE / args.raw
    if not raw_path.exists():
        print(f"{raw_path.name} not found — run extract.py first.")
        return 1

    data = json.loads(raw_path.read_text(encoding="utf-8"))
    rows = []
    for f in data["features"]:
        p = f["properties"]
        lon, lat, depth = f["geometry"]["coordinates"]
        rows.append({
            "id": f["id"],
            "time_ms": p["time"],
            "place": p["place"],
            "mag": p["mag"],
            "depth_km": depth,
            "latitude": lat,
            "longitude": lon,
            "felt": p["felt"],
            "tsunami": p["tsunami"],
            "significance": p["sig"],
            "event_type": p["type"],
        })
    df = pd.DataFrame(rows)
    raw_count = len(df)

    # --- cleaning (explicit rules) -------------------------------------
    df = df[df["event_type"] == "earthquake"]          # drop blasts etc.
    df = df.dropna(subset=["mag", "place"])             # unusable rows
    df = df.drop_duplicates(subset=["id"])              # one row per event
    df["felt"] = df["felt"].fillna(0).astype(int)       # no reports = 0
    df["tsunami"] = df["tsunami"].fillna(0).astype(int)

    utc = pd.to_datetime(df["time_ms"], unit="ms", utc=True)
    df["occurred_at_utc"] = utc.dt.strftime("%Y-%m-%d %H:%M:%S")
    df["occurred_at_ist"] = (utc.dt.tz_convert("Asia/Kolkata")
                             .dt.strftime("%Y-%m-%d %H:%M:%S"))
    df["region"] = df["place"].str.rsplit(",", n=1).str[-1].str.strip()
    df["mag_band"] = df["mag"].apply(mag_band)
    df = df.sort_values("time_ms").reset_index(drop=True)

    # --- data-quality checks (fail loudly) ------------------------------
    problems = []
    if df["id"].duplicated().any():
        problems.append("duplicate event ids remain")
    if not df["mag"].between(-2, 10).all():
        problems.append("magnitude outside sane range (-2..10)")
    if not df["depth_km"].between(-10, 750).all():
        problems.append("depth outside sane range (-10..750 km)")
    if df["occurred_at_utc"].isna().any():
        problems.append("unparsed timestamps present")
    if problems:
        for p in problems:
            print(f"QUALITY CHECK FAILED: {p}")
        return 1

    cols = ["id", "occurred_at_utc", "occurred_at_ist", "place", "region",
            "mag", "mag_band", "depth_km", "latitude", "longitude",
            "felt", "tsunami", "significance"]
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df[cols].to_csv(OUT_PATH, index=False)

    print(f"Raw features   : {raw_count}")
    print(f"Clean rows     : {len(df)} "
          f"({raw_count - len(df)} removed by cleaning rules)")
    print(f"Window (UTC)   : {df['occurred_at_utc'].min()} → "
          f"{df['occurred_at_utc'].max()}")
    print(f"Magnitude range: {df['mag'].min()} → {df['mag'].max()}")
    print(f"Saved (clean)  : data/processed/{OUT_PATH.name}")
    print("All quality checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
