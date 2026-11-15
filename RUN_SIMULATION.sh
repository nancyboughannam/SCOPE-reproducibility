#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [ ! -x .venv/bin/python ]; then echo 'Run bash SETUP.sh first.' >&2; exit 1; fi
if [ "$(uname -s)" = Darwin ]; then
  exec caffeinate -i .venv/bin/python reproduce.py run "$@"
fi
exec .venv/bin/python reproduce.py run "$@"
