#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [ ! -x .venv/bin/python ]; then echo 'Run bash SETUP.sh first.' >&2; exit 1; fi
SOURCE="${1:-archived}"
if [ "$#" -gt 0 ]; then shift; fi
exec .venv/bin/python reproduce.py package --source "$SOURCE" "$@"
