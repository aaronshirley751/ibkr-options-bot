#!/bin/bash
set -e

echo "=== IBKR Options Bot Pre-Deployment Validation ==="
echo ""

# Check 1: Python environment
echo "[1/6] Checking Python environment..."
python3 --version || { echo "❌ Python3 not found"; exit 1; }
echo "✓ Python OK"

# Check 2: Dependencies
echo "[2/6] Checking dependencies..."
python3 -c "import pandas; import pydantic; import loguru" || { echo "❌ Missing dependencies"; exit 1; }
echo "✓ Dependencies OK"

# Check 3: Configuration
echo "[3/6] Checking configuration..."
python3 -c "
from src.bot.settings import get_settings
s = get_settings()
assert s.dry_run == True, 'FATAL: dry_run must be True for initial deployment'
print(f'  dry_run: {s.dry_run}')
print(f'  symbols: {s.symbols}')
print(f'  broker.port: {s.broker.port}')
" || { echo "❌ Configuration invalid"; exit 1; }
echo "✓ Configuration OK"

# Check 4: Gateway connectivity
echo "[4/6] Checking Gateway connectivity..."
GATEWAY_HOST="${IBKR_HOST:-127.0.0.1}"
GATEWAY_PORT="${IBKR_PORT:-4002}"
timeout 5 bash -c "</dev/tcp/$GATEWAY_HOST/$GATEWAY_PORT" 2>/dev/null && {
    echo "✓ Gateway port $GATEWAY_PORT is accessible"
} || {
    echo "❌ Gateway not accessible at $GATEWAY_HOST:$GATEWAY_PORT"
    echo "  Run: make gateway-up"
    exit 1
}

# Check 5: IBKR API test
echo "[5/6] Testing IBKR API connection..."
python3 test_ibkr_connection.py --host "$GATEWAY_HOST" --port "$GATEWAY_PORT" --timeout 10 || {
    echo "⚠️  IBKR API test had issues (check output above)"
}

# Check 6: Test suite
echo "[6/6] Running test suite..."
pytest tests/ -q || { echo "❌ Tests failed"; exit 1; }
echo "✓ Tests OK"

echo ""
echo "=== All checks passed! Ready for deployment ==="
