I'll conduct a comprehensive Round 4 QA review of your IBKR Options Trading Bot. Let me first check our past conversations for additional context on the project state.Good, I have context from our Round 3 discussions. Let me now examine the current codebase state to conduct a thorough Round 4 audit.Let me examine the key code files from the provided documents to conduct a comprehensive Round 4 review. Based on the extensive documentation provided, I'll analyze the current state systematically.

---

# Round 4 QA Review: IBKR Options Trading Bot

**Date:** December 12, 2025  
**Status:** 🟢 **DEPLOYMENT READY** (pending Gateway validation)  
**Test Results:** 116/116 tests passing  
**Previous Rounds:** 3 completed (all critical issues resolved)

---

## Executive Summary

The codebase has matured significantly through 3 rounds of QA. All critical syntax errors, thread-safety issues, and safety concerns from Rounds 1-3 have been resolved. The project is architecturally sound and code-complete for Phase 1 paper trading.

**Primary Blocker:** IBKR Gateway connectivity validation on target Pi hardware remains the only deployment blocker.

**Round 4 Focus:** This review focuses on deployment readiness, hardening for production stability, and providing actionable prompts for Gateway resolution.

---

## 🚨 CRITICAL: Gateway Validation (Deployment Blocker)

**Status:** NOT VALIDATED - This is the #1 priority before deployment.

The codebase is ready. The infrastructure is not yet proven. All Gateway resolution options have been documented but none tested on target hardware.

---

## Round 4 Findings

### ✅ Issues Resolved from Previous Rounds

| Issue | Status | Verified In |
|-------|--------|-------------|
| emulate_oco indentation | ✅ Fixed | src/bot/execution.py |
| dry_run default | ✅ True | configs/settings.yaml |
| Race condition in save_equity_state | ✅ Fixed | src/bot/risk.py |
| Discord webhook support | ✅ Added | src/bot/monitoring.py |
| SIGTERM handler | ✅ Added | src/bot/app.py |
| Thread-safety locks | ✅ Added | whale_rules.py, scheduler.py |
| max_duration test | ✅ Added | tests/test_execution.py |
| Pi-optimized settings | ✅ Applied | configs/settings.yaml |

---

### 🔵 NEW: Round 4 Recommendations

#### Issue R4-1: Missing Broker Reconnection Logic (HIGH)

**Location:** `src/bot/scheduler.py` `process_symbol()`  
**Problem:** If broker disconnects mid-cycle, individual symbol processing fails silently without attempting reconnection.

**Copilot Prompt:**
```
In src/bot/scheduler.py, add broker reconnection logic at the start of process_symbol(). Before processing any symbol, verify broker connectivity and attempt reconnection if needed:

def process_symbol(symbol: str):
    try:
        # Verify broker connectivity first (add this block)
        if hasattr(broker, 'is_connected') and callable(broker.is_connected):
            if not broker.is_connected():
                logger.warning("Broker disconnected; attempting reconnection for %s", symbol)
                try:
                    broker.connect()
                    logger.info("Broker reconnected successfully")
                except Exception as conn_err:
                    logger.error("Failed to reconnect broker: %s: %s", type(conn_err).__name__, str(conn_err))
                    return  # Skip this symbol if reconnection fails
        
        # ... existing code continues ...
```

---

#### Issue R4-2: Missing Test Coverage Report in CI (MEDIUM)

**Location:** `.github/workflows/ci.yml`  
**Problem:** CI runs tests but doesn't generate or track coverage. No visibility into coverage trends.

**Copilot Prompt:**
```
Update .github/workflows/ci.yml to include coverage reporting:

      - name: Run tests with coverage
        run: |
          pytest tests/ -q --cov=src/bot --cov-report=xml --cov-report=term-missing --cov-fail-under=25

      - name: Upload coverage to Codecov (optional)
        uses: codecov/codecov-action@v4
        with:
          file: ./coverage.xml
          fail_ci_if_error: false
        continue-on-error: true

The --cov-fail-under=25 enforces minimum 25% coverage (current baseline). Increase as coverage improves.
```

---

#### Issue R4-3: Hardcoded Test Timeout in emulate_oco Test (LOW)

**Location:** `tests/test_execution.py` line ~185  
**Problem:** Test uses `max_duration_seconds=0.1` which is timing-sensitive and could cause flaky tests on slower systems.

**Copilot Prompt:**
```
In tests/test_execution.py test_emulate_oco_max_duration_exit(), make the test more robust by using mocking instead of real time:

def test_emulate_oco_max_duration_exit(self):
    """Emulation exits when max_duration_seconds is exceeded."""
    broker = Mock()
    contract = Mock(symbol="SPY")
    
    # Price never hits TP or SL
    broker.market_data = Mock(return_value=Mock(last=2.50))
    
    # Mock time to simulate duration exceeded
    with patch('src.bot.execution.time.sleep', return_value=None) as mock_sleep, \
         patch('src.bot.execution.time') as mock_time_module:
        # Simulate time advancing past max_duration
        mock_time_module.time = Mock(side_effect=[0, 0.1, 0.2, 100000])  # Last call exceeds duration
        mock_time_module.sleep = Mock()
        
        with patch('src.bot.execution.logger') as mock_logger:
            emulate_oco(
                broker,
                contract,
                parent_order_id="PARENT_DUR",
                take_profit=5.0,
                stop_loss=1.0,
                poll_seconds=1,
                side="BUY",
                quantity=1,
                max_duration_seconds=10,
            )
        
        # Verify warning was logged about max duration
        assert any("max duration" in str(call).lower() for call in mock_logger.warning.call_args_list)
```

---

#### Issue R4-4: No Startup Validation of Configuration (MEDIUM)

**Location:** `src/bot/app.py`  
**Problem:** Bot starts without validating critical settings (e.g., broker reachability, required env vars). Failures occur later in the cycle.

**Copilot Prompt:**
```
In src/bot/app.py main(), add startup validation before entering the scheduler loop:

def main():
    logger.info("Starting ibkr-options-bot")
    settings = get_settings()
    
    # Startup validation (add this block)
    logger.info("Validating configuration...")
    
    # Validate dry_run for initial deployment
    if not settings.dry_run:
        logger.warning("⚠️  dry_run is FALSE - orders WILL be executed!")
    else:
        logger.info("✓ dry_run mode enabled (safe for testing)")
    
    # Validate symbols configured
    if not settings.symbols:
        logger.error("No symbols configured in settings")
        return
    logger.info("✓ Symbols configured: %s", settings.symbols)
    
    # Validate risk settings
    if settings.risk.max_daily_loss_pct > 0.20:
        logger.warning("⚠️  max_daily_loss_pct (%.1f%%) is high", settings.risk.max_daily_loss_pct * 100)
    logger.info("✓ Risk settings: max_daily_loss=%.1f%%, max_risk_per_trade=%.1f%%", 
                settings.risk.max_daily_loss_pct * 100, 
                settings.risk.max_risk_pct_per_trade * 100)
    
    # Log monitoring status
    if settings.monitoring.alerts_enabled:
        alert_channels = []
        if settings.monitoring.discord_webhook_url:
            alert_channels.append("Discord")
        if settings.monitoring.slack_webhook_url:
            alert_channels.append("Slack")
        if settings.monitoring.telegram_bot_token:
            alert_channels.append("Telegram")
        logger.info("✓ Alerts enabled: %s", ", ".join(alert_channels) or "None configured")
    else:
        logger.info("ℹ️  Alerts disabled")
    
    logger.info("Configuration validation complete")
    
    # ... rest of existing main() code ...
```

---

#### Issue R4-5: No Graceful Cycle Skip on Market Data Failure (MEDIUM)

**Location:** `src/bot/scheduler.py` `process_symbol()`  
**Problem:** When `broker.historical_prices()` fails, the symbol is skipped but no aggregated metric tracks how many symbols failed per cycle.

**Copilot Prompt:**
```
In src/bot/scheduler.py, add cycle-level metrics tracking for observability:

# Add at module level after imports
_cycle_metrics: Dict[str, int] = {}
_cycle_metrics_lock = Lock()

def _reset_cycle_metrics():
    global _cycle_metrics
    with _cycle_metrics_lock:
        _cycle_metrics = {
            "symbols_processed": 0,
            "symbols_skipped": 0,
            "signals_generated": 0,
            "orders_placed": 0,
            "errors": 0,
        }

def _increment_metric(key: str, value: int = 1):
    with _cycle_metrics_lock:
        _cycle_metrics[key] = _cycle_metrics.get(key, 0) + value

# At the start of run_cycle():
def run_cycle(broker, settings: Dict[str, Any]):
    _reset_cycle_metrics()
    # ... existing code ...

# At the end of process_symbol(), log metric:
# After successful signal:
_increment_metric("signals_generated")

# After successful order:
_increment_metric("orders_placed")

# After any skip:
_increment_metric("symbols_skipped")

# After any error:
_increment_metric("errors")

# At end of run_cycle(), after ThreadPoolExecutor completes:
logger.bind(event="cycle_complete", metrics=_cycle_metrics).info(
    "Cycle complete: processed=%d skipped=%d signals=%d orders=%d errors=%d",
    _cycle_metrics.get("symbols_processed", 0),
    _cycle_metrics.get("symbols_skipped", 0),
    _cycle_metrics.get("signals_generated", 0),
    _cycle_metrics.get("orders_placed", 0),
    _cycle_metrics.get("errors", 0),
)
```

---

#### Issue R4-6: StubBroker Should Be Shared Fixture (LOW)

**Location:** `tests/test_scheduler_stubbed.py`  
**Problem:** StubBroker is defined inline; other tests could benefit from reusing it.

**Copilot Prompt:**
```
Create tests/conftest.py with shared test fixtures:

"""Shared pytest fixtures for IBKR bot tests."""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List

import pandas as pd
import pytest


@dataclass
class StubQuote:
    """Simulated market quote for testing."""
    symbol: str
    last: float
    bid: float
    ask: float
    volume: int


@dataclass
class StubOption:
    """Simulated option contract for testing."""
    symbol: str
    right: str
    strike: float
    expiry: str
    multiplier: int = 100


class StubBroker:
    """Deterministic broker for testing without IBKR connectivity."""
    
    def __init__(self, equity: float = 100000.0):
        self._equity = equity
        self._orders: List[Dict[str, Any]] = []
        self._connected = True
    
    def is_connected(self) -> bool:
        return self._connected
    
    def connect(self) -> None:
        self._connected = True
    
    def disconnect(self) -> None:
        self._connected = False
    
    def market_data(self, symbol_or_contract):
        if isinstance(symbol_or_contract, str):
            return StubQuote(symbol_or_contract, last=100.0, bid=99.9, ask=100.1, volume=1_000_000)
        return StubQuote(
            getattr(symbol_or_contract, "symbol", "OPT"),
            last=2.5, bid=2.45, ask=2.55, volume=5000
        )
    
    def option_chain(self, symbol: str, expiry_hint: str = "weekly"):
        strikes = [99, 100, 101]
        return [
            StubOption(f"{symbol}C{k}", "C", k, "20250117") for k in strikes
        ] + [
            StubOption(f"{symbol}P{k}", "P", k, "20250117") for k in strikes
        ]
    
    def historical_prices(self, symbol: str, duration: str = "60 M", bar_size: str = "1 min", **_):
        idx = pd.date_range(end=datetime.now(timezone.utc), periods=60, freq="1min")
        close = pd.Series([100 + i * 0.01 for i in range(60)], index=idx)
        return pd.DataFrame({
            "open": close, "high": close + 0.05, "low": close - 0.05,
            "close": close, "volume": pd.Series([1000] * 60, index=idx)
        })
    
    def place_order(self, ticket):
        self._orders.append({"action": ticket.action, "qty": ticket.quantity})
        return f"OID{len(self._orders)}"
    
    def pnl(self) -> Dict[str, float]:
        return {"net": self._equity}


@pytest.fixture
def stub_broker():
    """Provide a fresh StubBroker instance."""
    return StubBroker()


@pytest.fixture
def sample_settings():
    """Provide minimal valid settings for testing."""
    return {
        "symbols": ["SPY"],
        "mode": "growth",
        "dry_run": True,
        "risk": {
            "max_risk_pct_per_trade": 0.01,
            "stop_loss_pct": 0.2,
            "take_profit_pct": 0.3,
            "max_daily_loss_pct": 0.15,
        },
        "options": {"moneyness": "atm", "min_volume": 100, "max_spread_pct": 5.0},
        "schedule": {"interval_seconds": 1, "max_concurrent_symbols": 1},
        "monitoring": {"alerts_enabled": False},
    }


Then update tests/test_scheduler_stubbed.py to import from conftest instead of defining inline.
```

---

## Gateway Installation & Validation Prompts

These prompts are designed for direct execution on your Raspberry Pi:

### Gateway Prompt 1: Automated Gateway Resolution Script

**Run on Pi:**
```bash
# SSH into Pi first
ssh pi@<your-pi-ip>
cd ~/ibkr-options-bot

# Make the test script executable and run it
chmod +x scripts/test_gateway_options.sh
bash scripts/test_gateway_options.sh
```

**Copilot Prompt (If script needs debugging):**
```
Debug scripts/test_gateway_options.sh on Raspberry Pi. The script should:
1. Test GHCR authentication (if user has set it up)
2. Try vnexus/ib-gateway:latest image
3. Try universalappfactory/ib-gateway image
4. For each option: pull image, start container, check port 4002, run make ibkr-test
5. Report which option works and update docker-compose.gateway.yml

If errors occur, add better error messages and fallback handling. Ensure the script:
- Checks if Docker is running before attempting pulls
- Handles network timeouts gracefully
- Preserves the original docker-compose.gateway.yml as backup
```

---

### Gateway Prompt 2: GHCR Authentication Setup

**Copilot Prompt (for user guidance):**
```
Create docs/GHCR_AUTHENTICATION.md with step-by-step instructions for authenticating to GitHub Container Registry on Raspberry Pi:

# GHCR Authentication for IBKR Gateway Image

## Prerequisites
- GitHub account with access to the ibkr-gateway repository
- Docker installed on your Raspberry Pi

## Step 1: Create Personal Access Token (PAT)

1. Go to https://github.com/settings/tokens
2. Click "Generate new token (classic)"
3. Give it a descriptive name: "Pi Gateway Access"
4. Set expiration: 90 days (recommended for security)
5. Select scopes:
   - ✅ `read:packages` (required)
6. Click "Generate token"
7. **Copy the token immediately** - you won't see it again!

## Step 2: Authenticate on Pi

SSH into your Pi and run:

```bash
# Replace YOUR_GITHUB_USERNAME with your GitHub username
# When prompted for password, paste your PAT (not your GitHub password)
docker login ghcr.io -u YOUR_GITHUB_USERNAME

# Or use this one-liner (replace placeholders):
echo "YOUR_PAT_TOKEN" | docker login ghcr.io -u YOUR_GITHUB_USERNAME --password-stdin
```

## Step 3: Verify Authentication

```bash
# Test pulling the image
docker pull ghcr.io/gyrasol/ibkr-gateway:latest

# If successful, you should see download progress
# If denied, double-check your token has read:packages scope
```

## Step 4: Start Gateway

```bash
cd ~/ibkr-options-bot
make gateway-up
docker ps  # Should show ibkr-gateway container running
```

## Troubleshooting

### "denied" error
- Verify your PAT has `read:packages` scope
- Make sure you're using the PAT as password, not your GitHub password
- Re-authenticate: `docker logout ghcr.io && docker login ghcr.io`

### "unauthorized" error
- Your PAT may have expired - generate a new one
- Check you have access to the gyrasol/ibkr-gateway repository

### Token storage
Docker stores credentials in ~/.docker/config.json. To remove:
```bash
docker logout ghcr.io
```
```

---

### Gateway Prompt 3: Manual IB Gateway Installation (Fallback)

**Copilot Prompt:**
```
Create docs/MANUAL_GATEWAY_INSTALL.md for installing IB Gateway directly on Raspberry Pi without Docker:

# Manual IB Gateway Installation on Raspberry Pi

Use this guide if Docker-based Gateway options fail.

## Prerequisites
- Raspberry Pi 4/5 with 4GB+ RAM
- 64-bit Raspberry Pi OS (Bookworm recommended)
- Desktop environment (for initial setup)
- IBKR paper trading account

## Step 1: Download IB Gateway

```bash
# Download the offline installer (Linux)
wget https://download2.interactivebrokers.com/installers/ibgateway/stable-standalone/ibgateway-stable-standalone-linux-x64.sh

# Make executable
chmod +x ibgateway-stable-standalone-linux-x64.sh
```

## Step 2: Install IB Gateway

```bash
# Run installer (requires GUI or VNC)
./ibgateway-stable-standalone-linux-x64.sh

# Follow the installation wizard
# Default install location: ~/Jts/ibgateway
```

## Step 3: Configure IB Gateway

1. Launch IB Gateway (first time requires GUI)
2. Log in with your paper trading credentials
3. Go to Configure > Settings > API > Settings:
   - ✅ Enable ActiveX and Socket Clients
   - ✅ Socket port: 4002
   - ✅ Allow connections from localhost only (for security)
   - ✅ Read-Only API: Unchecked (allows order placement)
4. Save settings

## Step 4: Create Startup Script

```bash
cat > ~/start_gateway.sh << 'EOF'
#!/bin/bash
# Start IB Gateway in headless mode
cd ~/Jts/ibgateway
./ibgateway &
sleep 30  # Wait for startup
# Check if port is open
nc -zv localhost 4002 && echo "Gateway started successfully" || echo "Gateway failed to start"
EOF

chmod +x ~/start_gateway.sh
```

## Step 5: Update Bot Configuration

Edit .env:
```
IBKR_HOST=127.0.0.1
IBKR_PORT=4002
```

## Step 6: Test Connection

```bash
cd ~/ibkr-options-bot
source .venv/bin/activate
python test_ibkr_connection.py --host 127.0.0.1 --port 4002 --timeout 10
```

## Running Gateway at Boot (Optional)

Create systemd service for auto-start:
```bash
# Create service file
sudo cat > /etc/systemd/system/ibgateway.service << EOF
[Unit]
Description=IB Gateway
After=network.target

[Service]
Type=simple
User=pi
ExecStart=/home/pi/start_gateway.sh
Restart=on-failure
RestartSec=30

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl enable ibgateway
sudo systemctl start ibgateway
```
```

---

### Gateway Prompt 4: Complete Deployment Validation

**Copilot Prompt:**
```
Create scripts/full_deployment_check.sh that performs comprehensive pre-deployment validation:

#!/bin/bash
set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "╔════════════════════════════════════════════════════════════╗"
echo "║     IBKR Options Bot - Full Deployment Validation         ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

ERRORS=0
WARNINGS=0

# Function to report status
check_pass() { echo -e "${GREEN}✓${NC} $1"; }
check_fail() { echo -e "${RED}✗${NC} $1"; ((ERRORS++)); }
check_warn() { echo -e "${YELLOW}⚠${NC} $1"; ((WARNINGS++)); }

echo "═══ Environment Checks ═══"

# Python version
PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
if [[ "${PYTHON_VERSION}" =~ ^3\.1[1-9] ]]; then
    check_pass "Python ${PYTHON_VERSION}"
else
    check_warn "Python ${PYTHON_VERSION} (3.11+ recommended)"
fi

# Virtual environment
if [ -d ".venv" ] && [ -f ".venv/bin/activate" ]; then
    check_pass "Virtual environment exists"
    source .venv/bin/activate
else
    check_fail "Virtual environment missing (run: make venv)"
fi

# Dependencies
python3 -c "import pandas; import pydantic; import loguru; import ib_insync" 2>/dev/null && \
    check_pass "Core dependencies installed" || \
    check_fail "Missing dependencies (run: pip install -r requirements.txt)"

echo ""
echo "═══ Configuration Checks ═══"

# Settings validation
python3 -c "
from src.bot.settings import get_settings
s = get_settings()
print(f'dry_run: {s.dry_run}')
print(f'symbols: {s.symbols}')
print(f'interval: {s.schedule.interval_seconds}s')
print(f'max_daily_loss: {s.risk.max_daily_loss_pct*100:.1f}%')
exit(0 if s.dry_run else 1)
" 2>/dev/null && \
    check_pass "dry_run is TRUE (safe mode)" || \
    check_fail "dry_run is FALSE - DANGER: Real orders will execute!"

# .env file
if [ -f ".env" ]; then
    check_pass ".env file exists"
    # Check for required vars
    grep -q "IBKR_USERNAME" .env && check_pass "IBKR_USERNAME configured" || check_warn "IBKR_USERNAME not in .env"
    grep -q "IBKR_PASSWORD" .env && check_pass "IBKR_PASSWORD configured" || check_warn "IBKR_PASSWORD not in .env"
else
    check_fail ".env file missing (copy from .env.example)"
fi

echo ""
echo "═══ Gateway Connectivity ═══"

GATEWAY_HOST="${IBKR_HOST:-127.0.0.1}"
GATEWAY_PORT="${IBKR_PORT:-4002}"

# Check if gateway port is open
if timeout 3 bash -c "</dev/tcp/$GATEWAY_HOST/$GATEWAY_PORT" 2>/dev/null; then
    check_pass "Gateway port $GATEWAY_PORT accessible"
    
    # Run full connectivity test
    echo "   Running IBKR API test..."
    if python3 test_ibkr_connection.py --host "$GATEWAY_HOST" --port "$GATEWAY_PORT" --timeout 10 2>/dev/null | grep -q "stock_snapshot"; then
        check_pass "IBKR API responding with market data"
    else
        check_warn "IBKR API connected but no market data (may be outside market hours)"
    fi
else
    check_fail "Gateway not accessible at $GATEWAY_HOST:$GATEWAY_PORT"
    echo "       Run: make gateway-up"
fi

echo ""
echo "═══ Test Suite ═══"

# Run tests
if pytest tests/ -q --tb=no 2>/dev/null | grep -q "passed"; then
    PASSED=$(pytest tests/ -q --tb=no 2>&1 | grep -oP '\d+(?= passed)')
    check_pass "Test suite: $PASSED tests passed"
else
    check_fail "Test suite failed (run: pytest tests/ -v)"
fi

echo ""
echo "═══ Code Quality ═══"

# Syntax check
python3 -m py_compile src/bot/app.py src/bot/scheduler.py src/bot/execution.py 2>/dev/null && \
    check_pass "Core modules syntax valid" || \
    check_fail "Syntax errors in core modules"

# Black check (optional)
if command -v black &> /dev/null; then
    black --check src tests 2>/dev/null && \
        check_pass "Code formatting (black)" || \
        check_warn "Code needs formatting (run: black src tests)"
fi

echo ""
echo "════════════════════════════════════════════════════════════"
if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}DEPLOYMENT READY${NC} ($WARNINGS warnings)"
    echo ""
    echo "Next steps:"
    echo "  1. Start bot: python -m src.bot.app"
    echo "  2. Monitor logs: tail -f logs/bot.log"
    echo "  3. Watch for cycle completion messages"
else
    echo -e "${RED}NOT READY${NC} - $ERRORS errors, $WARNINGS warnings"
    echo ""
    echo "Fix the errors above before deploying."
fi
echo "════════════════════════════════════════════════════════════"

exit $ERRORS
```

---

## Deployment Priority Matrix

| Priority | Task | Time | Status |
|----------|------|------|--------|
| 🔴 P0 | Gateway validation on Pi | 30-60 min | **BLOCKER** |
| 🟠 P1 | Run full_deployment_check.sh | 5 min | After Gateway |
| 🟠 P1 | Verify dry_run=true | 1 min | ✅ Done |
| 🟡 P2 | Add broker reconnection logic | 15 min | Optional |
| 🟡 P2 | Add startup validation | 10 min | Recommended |
| 🟢 P3 | Coverage reporting in CI | 10 min | Post-deploy |
| 🟢 P3 | Extract StubBroker to conftest | 10 min | Code quality |
| 🟢 P3 | Cycle metrics tracking | 20 min | Observability |

---

## Final Pre-Deployment Checklist

```
Gateway Resolution (CRITICAL - Do First)
□ SSH into Pi: ssh pi@<your-pi-ip>
□ Navigate to repo: cd ~/ibkr-options-bot
□ Run gateway test: bash scripts/test_gateway_options.sh
□ If GHCR fails, try VNC gateway: cp docker-compose.gateway-vnexus.yml docker-compose.gateway.yml
□ Start gateway: make gateway-up
□ Verify running: docker ps | grep gateway
□ Test connectivity: make ibkr-test

Configuration Verification
□ dry_run: true (CRITICAL)
□ symbols: ["SPY"] only
□ interval_seconds: 300
□ max_concurrent_symbols: 1
□ Discord webhook URL (optional)

Code Verification
□ All 116 tests pass: pytest tests/ -v
□ Syntax valid: python -m py_compile src/bot/*.py
□ Settings load: python -c "from src.bot.settings import get_settings; print(get_settings())"

Deployment
□ Run full check: bash scripts/full_deployment_check.sh
□ Start bot: python -m src.bot.app
□ Monitor logs: tail -f logs/bot.log
□ Verify first cycle completes without errors
□ Check for order submission (should be dry_run logged)
```

---

## Summary

**Round 4 Assessment: DEPLOYMENT READY (pending Gateway validation)**

The codebase is mature, well-tested (116 tests passing), and implements all required safety measures:
- Thread-safe operations
- Daily loss guards with persistence
- Conservative Pi-optimized settings
- dry_run protection enabled
- Discord webhook alerting ready
- Graceful shutdown handling

**Remaining Action Items:**
1. **CRITICAL:** Validate Gateway connectivity on Pi (30-60 min)
2. **RECOMMENDED:** Add broker reconnection logic (15 min)
3. **OPTIONAL:** Add startup validation logging (10 min)

**Confidence Level:** High - The codebase architecture is sound. Once Gateway is validated, Phase 1 paper trading can begin immediately.

Would you like me to provide additional prompts for any specific aspect, or shall I elaborate on the Gateway resolution options?