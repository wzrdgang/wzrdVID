#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"
export PIP_CACHE_DIR="$PWD/.pip-cache"
mkdir -p "$PIP_CACHE_DIR"

if [ ! -x ".venv/bin/python" ]; then
  python3 -m venv .venv
fi

VENV_PYTHON="$PWD/.venv/bin/python"
"$VENV_PYTHON" -m pip install --upgrade pip
"$VENV_PYTHON" -m pip install -r requirements.txt
"$VENV_PYTHON" app.py
