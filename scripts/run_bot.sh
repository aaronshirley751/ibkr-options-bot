#!/usr/bin/env bash
set -euo pipefail
# Activates .venv and runs the bot
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="${ROOT_DIR}/.venv"
if [ -d "$VENV" ]; then
  # shellcheck disable=SC1090
  source "$VENV/bin/activate"
fi
exec python -m src.bot.app
