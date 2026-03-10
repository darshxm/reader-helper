#!/usr/bin/env bash
set -euo pipefail

# Ensure venv exists
if [[ ! -d ".venv" ]]; then
  printf "Error: .venv not found. Run ./setup.sh first.\n" >&2
  exit 1
fi

# Activate venv
# shellcheck disable=SC1091
source .venv/bin/activate

# Run app
python main.py
