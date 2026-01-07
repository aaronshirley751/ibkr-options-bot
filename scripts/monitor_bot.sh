#!/bin/bash
# Extended dry-run monitoring script
# Usage: ./scripts/monitor_bot.sh [duration_minutes] [gateway_host]
# Example: ./scripts/monitor_bot.sh 180 192.168.7.205

set -e

DURATION=${1:-180}  # Default 3 hours
GATEWAY_HOST=${2:-127.0.0.1}
WORKSPACE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${WORKSPACE_DIR}/.venv"
LOGS_DIR="${WORKSPACE_DIR}/logs"
MEMORY_LOG="${LOGS_DIR}/memory_${DURATION}min_$(date +%Y%m%d_%H%M%S).log"
SUMMARY_FILE="${LOGS_DIR}/summary_$(date +%Y%m%d_%H%M%S).txt"

mkdir -p "${LOGS_DIR}"

echo "=========================================="
echo "IBKR Bot Extended Dry-Run Monitor"
echo "=========================================="
echo "Duration: ${DURATION} minutes"
echo "Gateway: ${GATEWAY_HOST}"
echo "Workspace: ${WORKSPACE_DIR}"
echo "Memory log: ${MEMORY_LOG}"
echo "Summary: ${SUMMARY_FILE}"
echo "Started: $(date)"
echo "=========================================="

# Export gateway host for bot config
export BROKER__HOST="${GATEWAY_HOST}"

# Function to capture memory
capture_memory() {
    local pid=$1
    local elapsed=$2
    
    if ps -p "$pid" > /dev/null 2>&1; then
        # Get memory in MB (works on macOS and Linux)
        if command -v ps &> /dev/null; then
            if [[ "$OSTYPE" == "darwin"* ]]; then
                # macOS
                mem=$(ps -p "$pid" -o rss= | awk '{print $1/1024}')
            else
                # Linux
                mem=$(ps -p "$pid" -o rss= | awk '{print $1/1024}')
            fi
            echo "$(date '+%Y-%m-%d %H:%M:%S') | Elapsed: ${elapsed}s | Memory: ${mem}MB | PID: $pid" >> "$MEMORY_LOG"
        fi
    else
        echo "$(date '+%Y-%m-%d %H:%M:%S') | Process terminated at ${elapsed}s" >> "$MEMORY_LOG"
        return 1
    fi
    return 0
}

# Start bot in background
echo "Starting bot..."
cd "${WORKSPACE_DIR}"

if [ -f "${VENV_DIR}/bin/activate" ]; then
    source "${VENV_DIR}/bin/activate"
elif [ -f "${VENV_DIR}/Scripts/activate" ]; then
    source "${VENV_DIR}/Scripts/activate"
else
    echo "ERROR: Virtual environment not found at ${VENV_DIR}"
    exit 1
fi

# Start bot
python -m src.bot.app > "${LOGS_DIR}/bot_$(date +%Y%m%d_%H%M%S).log" 2>&1 &
BOT_PID=$!
echo "Bot started with PID: $BOT_PID"

START_TIME=$(date +%s)
DURATION_SECONDS=$((DURATION * 60))
SAMPLE_INTERVAL=300  # 5 minutes

# Monitor loop
echo "Monitoring for ${DURATION} minutes (sampling every ${SAMPLE_INTERVAL}s)..."
echo "Timestamp | Elapsed | Memory | PID" > "$MEMORY_LOG"

while true; do
    CURRENT_TIME=$(date +%s)
    ELAPSED=$((CURRENT_TIME - START_TIME))
    
    if [ $ELAPSED -ge $DURATION_SECONDS ]; then
        echo "Duration reached. Stopping bot..."
        kill $BOT_PID 2>/dev/null || true
        sleep 2
        if ps -p $BOT_PID > /dev/null 2>&1; then
            kill -9 $BOT_PID 2>/dev/null || true
        fi
        break
    fi
    
    capture_memory $BOT_PID $ELAPSED || {
        echo "Bot process died at $ELAPSED seconds"
        break
    }
    
    sleep $SAMPLE_INTERVAL
done

END_TIME=$(date +%s)
TOTAL_ELAPSED=$((END_TIME - START_TIME))

# Generate summary
{
    echo "=========================================="
    echo "Extended Dry-Run Summary"
    echo "=========================================="
    echo "Start: $(date -d @$START_TIME '+%Y-%m-%d %H:%M:%S')"
    echo "End: $(date -d @$END_TIME '+%Y-%m-%d %H:%M:%S')"
    echo "Total Duration: ${TOTAL_ELAPSED}s ($(( TOTAL_ELAPSED / 60 ))m $(( TOTAL_ELAPSED % 60 ))s)"
    echo ""
    echo "Memory Usage:"
    tail -n +2 "$MEMORY_LOG" | awk '{print $6}' | sort -n | awk 'BEGIN {count=0; sum=0; min=999999; max=0} {count++; sum+=$1; if ($1<min) min=$1; if ($1>max) max=$1} END {if (count>0) printf "  Min: %.1fMB | Max: %.1fMB | Avg: %.1fMB\n", min, max, sum/count}'
    echo ""
    echo "Bot Log Analysis:"
    BOT_LOG=$(ls -t "${LOGS_DIR}"/bot_*.log 2>/dev/null | head -1)
    if [ -f "$BOT_LOG" ]; then
        echo "  Log file: $BOT_LOG"
        echo "  Total lines: $(wc -l < "$BOT_LOG")"
        echo "  INFO count: $(grep -c "INFO" "$BOT_LOG" || echo 0)"
        echo "  WARNING count: $(grep -c "WARNING" "$BOT_LOG" || echo 0)"
        echo "  ERROR count: $(grep -c "ERROR" "$BOT_LOG" || echo 0)"
        echo ""
        echo "  Last 20 lines:"
        tail -n 20 "$BOT_LOG" | sed 's/^/    /'
    fi
    echo ""
    echo "=========================================="
} | tee "$SUMMARY_FILE"

echo ""
echo "Monitoring complete!"
echo "Files created:"
echo "  Memory log: $MEMORY_LOG"
echo "  Summary: $SUMMARY_FILE"
echo "  Bot log: ${LOGS_DIR}/bot_*.log"
echo ""
echo "Analyze with: python scripts/analyze_logs.py --bot-log <path>"
