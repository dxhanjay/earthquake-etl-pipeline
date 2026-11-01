"""
LOAD step — Earthquake ETL Pipeline.

Reads the cleaned CSV from transform.py, applies sql/schema.sql to a
SQLite database (data/quakes.db), and upserts every row.

Idempotent by design: `id` (the USGS event id) is the PRIMARY KEY and
rows are written with INSERT OR REPLACE inside one transaction, so
re-running the pipeline never duplicates an event — and when USGS
revises an event's magnitude or depth, the stored row updates.

Standard library only (sqlite3 + csv).

Run:  python load.py   (after transform.py)
"""

import csv
import sqlite3
import sys
from pathlib import Path

BASE = Path(__file__).parent
CSV_PATH = BASE / "data" / "processed" / "quakes_clean.csv"
SCHEMA_PATH = BASE / "sql" / "schema.sql"
DB_PATH = BASE / "data" / "quakes.db"

COLUMNS = ["id", "occurred_at_utc", "occurred_at_ist", "place", "region",
           "mag", "mag_band", "depth_km", "latitude", "longitude",
           "felt", "tsunami", "significance"]
FLOATS = {"mag", "depth_km", "latitude", "longitude"}
INTS = {"felt", "tsunami", "significance"}

UPSERT_SQL = f"""
INSERT OR REPLACE INTO earthquakes ({", ".join(COLUMNS)})
VALUES ({", ".join("?" for _ in COLUMNS)})
"""


def read_clean_csv(path: Path) -> list[tuple]:
    if not path.exists():
        raise FileNotFoundError(f"{path.name} not found — run transform.py first.")
    rows = []
    with path.open(newline="", encoding="utf-8") as f:
        for rec in csv.DictReader(f):
            row = []
            for col in COLUMNS:
                v = rec[col]
                if col in FLOATS:
                    row.append(float(v) if v != "" else None)
                elif col in INTS:
                    row.append(int(float(v)) if v != "" else None)
                else:
                    row.append(v)
            rows.append(tuple(row))
    return rows


def main() -> int:
    rows = read_clean_csv(CSV_PATH)
    if not rows:
        print("Clean CSV is empty — nothing to load.")
        return 1

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        before = conn.execute("SELECT COUNT(*) FROM earthquakes").fetchone()[0]
        with conn:
            conn.executemany(UPSERT_SQL, rows)
        after, first, last = conn.execute(
            "SELECT COUNT(*), MIN(occurred_at_utc), MAX(occurred_at_utc) "
            "FROM earthquakes").fetchone()
    finally:
        conn.close()

    print(f"Clean CSV rows : {len(rows)}")
    print(f"Table before   : {before} rows")
    print(f"Table after    : {after} rows ({after - before:+d} net new)")
    print(f"Coverage (UTC) : {first}  →  {last}")
    print(f"Database       : data/{DB_PATH.name}")
    print("Load complete — safe to re-run, events upsert by USGS id.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
