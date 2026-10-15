#!/usr/bin/env sh
# macOS / Linux: ./start_mac_linux.sh  (add --lan for tablets)
cd "$(dirname "$0")"
[ -x .venv/bin/python ] || { python3 -m venv .venv && .venv/bin/pip install -q -r requirements.txt; }
.venv/bin/python run.py --open "$@"
