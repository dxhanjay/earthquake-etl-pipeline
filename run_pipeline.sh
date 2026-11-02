#!/usr/bin/env bash
# One-command end-to-end run: extract -> transform -> load -> dashboard
#
#   ./run_pipeline.sh                                  # past-week feed
#   ./run_pipeline.sh --start 2026-10-01 --end 2026-11-01
#                                                      # historical backfill
# Historical runs load into the same database through the same idempotent
# upserts, so backfills extend the record without duplicating events.
set -e
cd "$(dirname "$0")"
if [ $# -gt 0 ]; then
  python3 extract.py "$@"
  python3 transform.py --raw data/raw/usgs_history.geojson
else
  python3 extract.py
  python3 transform.py
fi
python3 load.py
python3 build_dashboard.py
echo "Pipeline complete. Dashboard: site/index.html"
