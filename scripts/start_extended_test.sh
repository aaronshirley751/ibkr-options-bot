#!/bin/bash
# Extended Dry-Run Test Script
# Runs bot for extended period with Discord alerts enabled
# Usage: ./scripts/start_extended_test.sh [duration_minutes] [gateway_host]

set -e

DURATION=${1:-180}
GATEWAY_HOST=${2:-192.168.7.205}
WORKSPACE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${WORKSPACE_DIR}/.venv"
LOGS_DIR="${WORKSPACE_DIR}/logs"

echo "=========================================="
echo "Extended Dry-Run Test - Starting"
echo "=========================================="
echo "Duration: ${DURATION} minutes"
echo "Gateway: ${GATEWAY_HOST}"
echo "Workspace: ${WORKSPACE_DIR}"
echo "Started: $(date)"
echo ""

mkdir -p "${LOGS_DIR}"

# Activate venv
if [ -f "${VENV_DIR}/bin/activate" ]; then
    source "${VENV_DIR}/bin/activate"
elif [ -f "${VENV_DIR}/Scripts/activate" ]; then
    source "${VENV_DIR}/Scripts/activate"
else
    echo "ERROR: Virtual environment not found"
    exit 1
fi

# Update settings.yaml with gateway host
cd "${WORKSPACE_DIR}"

# Set environment and run
export BROKER__HOST="${GATEWAY_HOST}"
export DRY_RUN=true

# Create timestamped log
LOG_FILE="${LOGS_DIR}/test_$(date +%Y%m%d_%H%M%S).log"

echo "Bot log: $LOG_FILE"
echo "Running bot for ${DURATION} minutes..."
echo ""

# Run with timeout
timeout $((DURATION * 60)) python -m src.bot.app 2>&1 | tee "$LOG_FILE" || {
    exit_code=$?
    if [ $exit_code -eq 124 ]; then
        echo ""
        echo "=========================================="
        echo "✅ Test Duration Complete ($DURATION min)"
        echo "=========================================="
    else
        echo ""
        echo "⚠️ Bot exited with code: $exit_code"
    fi
}

echo ""
echo "Analysis: python scripts/analyze_logs.py --bot-log \"$LOG_FILE\""
