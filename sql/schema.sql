-- Earthquake ETL Pipeline — SQLite schema
--
-- One row per earthquake event. `id` is the USGS event id (natural key):
-- the same event can only appear once, which is what makes load.py
-- idempotent (re-running replaces rows instead of duplicating them).
-- USGS revises magnitudes/depths after review, so an upsert also keeps
-- stored values current with the latest feed.

CREATE TABLE IF NOT EXISTS earthquakes (
    id              TEXT PRIMARY KEY,        -- USGS event id
    occurred_at_utc TEXT NOT NULL,           -- 'YYYY-MM-DD HH:MM:SS' (UTC)
    occurred_at_ist TEXT NOT NULL,           -- same instant, Asia/Kolkata
    place           TEXT NOT NULL,
    region          TEXT NOT NULL,
    mag             REAL NOT NULL CHECK (mag BETWEEN -2 AND 10),
    mag_band        TEXT NOT NULL,
    depth_km        REAL CHECK (depth_km BETWEEN -10 AND 750),
    latitude        REAL,
    longitude       REAL,
    felt            INTEGER NOT NULL DEFAULT 0,  -- # of felt reports
    tsunami         INTEGER NOT NULL DEFAULT 0,  -- 1 = tsunami flag set
    significance    INTEGER,
    loaded_at       TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_quakes_date ON earthquakes (date(occurred_at_utc));
CREATE INDEX IF NOT EXISTS idx_quakes_mag  ON earthquakes (mag);
