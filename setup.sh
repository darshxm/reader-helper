#!/usr/bin/env bash
set -euo pipefail

# Create venv if it doesn't exist
if [[ ! -d ".venv" ]]; then
  python3 -m venv .venv
else
  printf ".venv already exists, skipping creation.\n"
fi

# Activate venv
# shellcheck disable=SC1091
source .venv/bin/activate

# Install dependencies
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

# Prompt for Gemini API key
read -r -s -p "Enter your Gemini API key: " GEMINI_API_KEY
printf "\n"

# Persist key to .env (create or update)
ENV_FILE=".env"
if [[ -f "$ENV_FILE" ]]; then
  # Remove existing key line if present
  grep -v '^GEMINI_API_KEY=' "$ENV_FILE" > "${ENV_FILE}.tmp" || true
  mv "${ENV_FILE}.tmp" "$ENV_FILE"
fi
printf "GEMINI_API_KEY=%s\n" "$GEMINI_API_KEY" >> "$ENV_FILE"

printf "\nSetup complete. Activate with: source .venv/bin/activate\n"
