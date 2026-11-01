#!/usr/bin/env bash
# One-command end-to-end run: extract -> transform -> load -> dashboard
set -e
cd "$(dirname "$0")"
python3 extract.py
python3 transform.py
python3 load.py
python3 build_dashboard.py
echo "Pipeline complete. Dashboard: site/index.html"
