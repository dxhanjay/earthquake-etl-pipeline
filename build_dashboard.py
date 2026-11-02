"""
DASHBOARD step — Earthquake ETL Pipeline.

Reads the loaded SQLite database (data/quakes.db) and renders a single
self-contained HTML dashboard into site/index.html — no JavaScript, no
external assets, deployable to any static host (the live copy runs on
Vercel). Every number on the page comes from a SQL query at build time;
rebuild after each pipeline run to refresh it.

Run:  python build_dashboard.py   (after load.py)
"""

import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).parent
DB_PATH = BASE / "data" / "quakes.db"
OUT_PATH = BASE / "site" / "index.html"


def q(conn, sql, args=()):
    return conn.execute(sql, args).fetchall()


def esc(s) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;"))


def main() -> int:
    if not DB_PATH.exists():
        print("quakes.db not found — run load.py first.")
        return 1
    conn = sqlite3.connect(DB_PATH)
    try:
        total, first, last = q(conn,
            "SELECT COUNT(*), MIN(occurred_at_utc), MAX(occurred_at_utc) "
            "FROM earthquakes")[0]
        strongest = q(conn,
            "SELECT mag, place, occurred_at_utc, depth_km FROM earthquakes "
            "ORDER BY mag DESC LIMIT 1")[0]
        deepest = q(conn,
            "SELECT mag, place, depth_km FROM earthquakes "
            "ORDER BY depth_km DESC LIMIT 1")[0]
        most_felt = q(conn,
            "SELECT mag, place, felt FROM earthquakes "
            "ORDER BY felt DESC LIMIT 1")[0]
        tsunami_n = q(conn,
            "SELECT COUNT(*) FROM earthquakes WHERE tsunami = 1")[0][0]
        felt_n = q(conn,
            "SELECT COUNT(*) FROM earthquakes WHERE felt > 0")[0][0]
        bands = q(conn,
            "SELECT mag_band, COUNT(*) FROM earthquakes "
            "GROUP BY mag_band ORDER BY MIN(mag)")
        top10 = q(conn,
            "SELECT mag, place, occurred_at_utc, depth_km, felt "
            "FROM earthquakes ORDER BY mag DESC LIMIT 10")
        per_day = q(conn,
            "SELECT date(occurred_at_utc), COUNT(*), MAX(mag) "
            "FROM earthquakes GROUP BY 1 ORDER BY 1")
        regions = q(conn,
            "SELECT region, COUNT(*), ROUND(AVG(mag),2), MAX(mag) "
            "FROM earthquakes GROUP BY region ORDER BY 2 DESC LIMIT 8")
    finally:
        conn.close()

    # Span-aware presentation: a week of data reads day by day; a longer
    # backfilled record aggregates to ISO weeks and renames the page.
    from datetime import date as _date, timedelta as _td
    first_d = _date.fromisoformat(first[:10])
    last_d = _date.fromisoformat(last[:10])
    span_days = (last_d - first_d).days
    history_mode = span_days > 10
    if history_mode:
        weekly: dict[str, list] = {}
        for d, c, m in per_day:
            monday = _date.fromisoformat(d)
            monday -= _td(days=monday.weekday())
            slot = weekly.setdefault(monday.isoformat(), [0, 0.0])
            slot[0] += c
            slot[1] = max(slot[1], m)
        per_period = [(f"Week of {k}", v[0], v[1])
                      for k, v in sorted(weekly.items())]
        period_label = "Events per week (UTC)"
    else:
        per_period = per_day
        period_label = "Events per day (UTC)"
    page_title = "The Historical Record" if history_mode else "This Week on Earth"

    band_max = max(c for _, c in bands) or 1
    band_rows = "\n".join(
        f'<div class="bar-row"><span class="bar-label">{esc(b)}</span>'
        f'<div class="bar-track"><div class="bar" '
        f'style="width:{max(3, round(c / band_max * 100))}%"></div></div>'
        f'<span class="bar-num">{c}</span></div>' for b, c in bands)
    day_max = max(c for _, c, _ in per_period) or 1
    day_rows = "\n".join(
        f'<div class="bar-row"><span class="bar-label">{d}</span>'
        f'<div class="bar-track"><div class="bar alt" '
        f'style="width:{max(3, round(c / day_max * 100))}%"></div></div>'
        f'<span class="bar-num">{c} (max M{m})</span></div>'
        for d, c, m in per_period)
    top_rows = "\n".join(
        f"<tr><td class='mag'>M{mag}</td><td>{esc(place)}</td>"
        f"<td>{utc}</td><td>{depth:.0f} km</td><td>{felt}</td></tr>"
        for mag, place, utc, depth, felt in top10)
    region_rows = "\n".join(
        f"<tr><td>{esc(r)}</td><td>{c}</td><td>{a}</td><td>M{m}</td></tr>"
        for r, c, a, m in regions)
    built = datetime.now(timezone.utc).strftime("%d %b %Y, %H:%M UTC")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Earthquake ETL — Live Dashboard</title>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family: Georgia, 'Times New Roman', serif; background:#0d1117;
         color:#e8e4da; padding:32px 18px 48px; }}
  .wrap {{ max-width:880px; margin:0 auto; }}
  h1 {{ font-size:30px; letter-spacing:.5px; }}
  h1 .accent {{ color:#e8a33d; }}
  .sub {{ color:#9a958a; margin:6px 0 24px; font-size:15px; }}
  .cards {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr));
           gap:12px; margin-bottom:26px; }}
  .card {{ background:#161b22; border:1px solid #2a2f38; border-radius:10px;
          padding:16px; }}
  .card .v {{ font-size:30px; color:#e8a33d; }}
  .card .k {{ color:#9a958a; font-size:13px; margin-top:4px; }}
  .card .d {{ font-size:13px; margin-top:6px; color:#cfc9bc; }}
  section {{ background:#161b22; border:1px solid #2a2f38; border-radius:10px;
            padding:20px; margin-bottom:18px; }}
  h2 {{ font-size:18px; margin-bottom:14px; color:#f0ead9; }}
  .bar-row {{ display:flex; align-items:center; gap:10px; margin:7px 0;
             font-size:13px; }}
  .bar-label {{ width:150px; color:#cfc9bc; flex:none; }}
  .bar-track {{ flex:1; background:#232830; border-radius:5px; height:16px; }}
  .bar {{ background:#e8a33d; height:16px; border-radius:5px; }}
  .bar.alt {{ background:#4d7fa8; }}
  .bar-num {{ width:110px; flex:none; color:#9a958a; }}
  table {{ width:100%; border-collapse:collapse; font-size:14px; }}
  td, th {{ padding:7px 8px; border-bottom:1px solid #232830; text-align:left; }}
  th {{ color:#9a958a; font-weight:normal; font-size:12px;
       text-transform:uppercase; letter-spacing:.06em; }}
  td.mag {{ color:#e8a33d; font-weight:bold; white-space:nowrap; }}
  footer {{ color:#6e6a61; font-size:13px; line-height:1.6; }}
  a {{ color:#e8a33d; }}
</style>
</head>
<body>
<div class="wrap">
  <h1>🌍 Earthquake <span class="accent">ETL</span> — {page_title}</h1>
  <p class="sub">USGS Magnitude 2.5+ earthquakes · {esc(first)} → {esc(last)} (UTC) ·
     extracted, cleaned, quality-checked and loaded by an automated pipeline ·
     dashboard generated {built}</p>

  <div class="cards">
    <div class="card"><div class="v">{total}</div><div class="k">earthquakes loaded</div>
      <div class="d">M2.5+ worldwide · {span_days + 1} days of loaded data</div></div>
    <div class="card"><div class="v">M{strongest[0]}</div><div class="k">strongest</div>
      <div class="d">{esc(strongest[1])} · {esc(strongest[2])} UTC · {strongest[3]:.0f} km deep</div></div>
    <div class="card"><div class="v">{deepest[2]:.0f} km</div><div class="k">deepest</div>
      <div class="d">M{deepest[0]} — {esc(deepest[1])}</div></div>
    <div class="card"><div class="v">{most_felt[2]}</div><div class="k">most felt reports</div>
      <div class="d">M{most_felt[0]} — {esc(most_felt[1])} · {felt_n} events felt by people</div></div>
    <div class="card"><div class="v">{tsunami_n}</div><div class="k">tsunami-flagged</div>
      <div class="d">events where USGS set the tsunami flag</div></div>
  </div>

  <section><h2>Events by magnitude band</h2>{band_rows}</section>
  <section><h2>{period_label}</h2>{day_rows}</section>
  <section><h2>🌋 The 10 strongest in the record</h2>
    <table><tr><th>Mag</th><th>Place</th><th>When (UTC)</th><th>Depth</th><th>Felt reports</th></tr>
    {top_rows}</table></section>
  <section><h2>Busiest regions</h2>
    <table><tr><th>Region</th><th>Events</th><th>Avg mag</th><th>Strongest</th></tr>
    {region_rows}</table></section>

  <footer>
    Built with an open-data ETL pipeline: USGS GeoJSON feed → pandas cleaning with
    data-quality checks → SQLite with idempotent upserts → SQL analysis → this page.
    Code: <a href="https://github.com/dxhanjay/earthquake-etl-pipeline">github.com/dxhanjay/earthquake-etl-pipeline</a> ·
    Data: U.S. Geological Survey (USGS), public domain.
  </footer>
</div>
</body>
</html>
"""
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(html, encoding="utf-8")
    print(f"Dashboard written: site/{OUT_PATH.name} ({len(html)} bytes)")
    print(f"Stats: {total} events | strongest M{strongest[0]} | "
          f"tsunami-flagged {tsunami_n} | felt events {felt_n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
