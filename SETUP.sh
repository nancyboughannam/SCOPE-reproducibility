#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
PYTHON="${SCOPE_PYTHON:-python3}"
"$PYTHON" -c 'import sys; assert (3,11) <= sys.version_info[:2] <= (3,12), "Use Python 3.11 or 3.12; set SCOPE_PYTHON to its executable."'
if [ ! -x .venv/bin/python ]; then "$PYTHON" -m venv .venv; fi
.venv/bin/python -m pip install -r requirements-reproducibility.txt
.venv/bin/python -m pip check
.venv/bin/python reproduce.py verify
echo 'SETUP COMPLETE. Archived figures can be plotted now. Simulation also requires JDK 21+.'
