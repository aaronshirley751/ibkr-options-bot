# Phase 3 Retry - Execution Playbook
## Step-by-Step Instructions

**Status**: Ready to Execute  
**Expected Duration**: 4-5 hours  
**Target**: 25+ complete cycles without timeout  

---

## Prerequisites Check

### 1. IBKR Gateway Running
```bash
# Verify Gateway is accessible at 192.168.7.205:4001
# TWS/Gateway should be running and login complete
nc -zv 192.168.7.205 4001
# Expected: Connection successful
```

### 2. Repository Updated
```bash
cd "c:\Users\tasms\my-new-project\Trading Bot\ibkr-options-bot"
git status
# Expected: working tree clean, on branch main
git log --oneline -3
# Should show: 6ef3aa6 (HEAD -> main) Add implementation summary
```

### 3. Python Environment Ready
```bash
# If not already set up:
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt -r requirements-dev.txt
```

---

## Configuration Setup

### Step 1: Backup Current Settings
```bash
# Preserve current configuration
copy configs\settings.yaml configs\settings.yaml.backup
```

### Step 2: Apply Phase 3 Conservative Settings
Edit `configs/settings.yaml` with these values:

```yaml
schedule:
  interval_seconds: 600           # Key: 10 minutes between cycles (was 180s)
  max_concurrent_symbols: 1       # Key: Sequential processing (was 2)

symbols:
  - SPY                           # Key: Single symbol for isolation

options:
  expiry: "weekly"
  moneyness: "atm"
  max_spread_pct: 2.0
  min_volume: 100
  strike_count: 3                 # Key: 40% fewer requests (was 5)

risk:
  max_risk_pct_per_trade: 0.01
  max_daily_loss_pct: 0.15
  take_profit_pct: 0.5
  stop_loss_pct: 0.2
  data_loss_exit_on_backoff: true

broker:
  host: 192.168.7.205
  port: 4001                      # Live account
  client_id: 100                  # Paper trading
  read_only: true                 # Dry-run mode

dry_run: true                      # CRITICAL: Stay in dry-run
paper: true                        # Use paper trading account

historical:
  duration: "7200 S"
  bar_size: "1 min"
  what_to_show: "TRADES"
  use_rth: false
```

### Step 3: Verify Configuration Loaded
```bash
# Test that settings parse correctly
.venv\Scripts\python -c "
from src.bot.settings import get_settings
s = get_settings()
print(f'Interval: {s.schedule.interval_seconds}')
print(f'Max concurrent: {s.schedule.max_concurrent_symbols}')
print(f'Symbols: {s.symbols}')
print(f'Strike count: {s.options.strike_count}')
print(f'Dry-run: {s.dry_run}')
"
# Expected output:
# Interval: 600
# Max concurrent: 1
# Symbols: ['SPY']
# Strike count: 3
# Dry-run: True
```

---

## Pre-Launch Tests

### Test 1: Gateway Connectivity
```bash
.venv\Scripts\python -c "
from src.bot.broker.ibkr import IBKR
from src.bot.settings import get_settings

settings = get_settings()
broker = IBKR(**settings.broker.model_dump())
print('Connecting...')
broker.connect()
print(f'Connected: {broker.is_connected()}')
print(f'Gateway healthy: {broker.is_gateway_healthy()}')
broker.disconnect()
print('Disconnected cleanly')
"
# Expected output:
# Connected: True
# Gateway healthy: True
# Disconnected cleanly
```

### Test 2: Circuit Breaker Logic
```bash
.venv\Scripts\python -c "
from src.bot.scheduler import GatewayCircuitBreaker
import time

cb = GatewayCircuitBreaker(failure_threshold=3, reset_timeout_seconds=2)

# Test normal operation
print(f'Initial state: {cb.state}, Should attempt: {cb.should_attempt()}')

# Record failures
cb.record_failure()
cb.record_failure()
cb.record_failure()
print(f'After 3 failures: {cb.state}, Should attempt: {cb.should_attempt()}')

# Wait for recovery timeout
time.sleep(2.5)
print(f'After timeout: {cb.state}, Should attempt: {cb.should_attempt()}')

# Record success
cb.record_success()
print(f'After success: {cb.state}, Should attempt: {cb.should_attempt()}')
"
# Expected output:
# Initial state: CLOSED, Should attempt: True
# After 3 failures: OPEN, Should attempt: False
# After timeout: HALF_OPEN, Should attempt: True
# After success: CLOSED, Should attempt: True
```

### Test 3: Unit Tests (Optional)
```bash
# Run all tests - should be 117 passing
.venv\Scripts\pytest tests/ -q
# Expected: 117 passed
```

---

## Execute Phase 3 Retry

### Step 1: Start Phase 3
```bash
# Open terminal in project root
cd "c:\Users\tasms\my-new-project\Trading Bot\ibkr-options-bot"

# Activate venv
.venv\Scripts\activate

# Run with 4-hour timeout (14400 seconds)
timeout 14400 python -m src.bot.app

# OR on Linux/Mac:
timeout 4h python -m src.bot.app
```

### Step 2: Monitor Logs in Separate Terminal
```bash
# Terminal 2: Watch real-time logs
# On Windows PowerShell:
Get-Content logs/bot.log -Wait

# OR on Windows CMD:
type logs/bot.log
# (refresh manually every minute)

# Look for:
# ✅ "Strategy decision" lines (every 600 seconds)
# ✅ "Cycle complete" messages
# ✅ Zero "historical_data_timeout" errors
# ✅ Circuit breaker stays in CLOSED state
# ❌ WARNING: "GatewayCircuitBreaker OPEN" (failure indicator)
```

### Step 3: Monitor JSON Events
```bash
# Terminal 3: Watch JSON events (live event stream)
# On Windows PowerShell:
Get-Content logs/bot.jsonl -Wait | Select-String "cycle_complete|historical_data_timeout"

# Look for patterns like:
# {"cycle": 1, "event": "cycle_complete", ...}
# {"cycle": 2, "event": "cycle_complete", ...}
# (25+ of these is success)
```

### Step 4: Monitor Resource Usage
```bash
# Terminal 4: Check memory and CPU
# On Windows:
tasklist /FI "IMAGENAME eq python.exe"

# On Linux/Mac:
watch -n 5 'ps aux | grep "[p]ython -m src.bot.app"'

# Expected: Stable memory (< 200MB), low CPU (< 10%)
```

---

## Success Indicators (Real-time)

### Every 10 minutes, you should see:
```
2026-01-09 08:45:23.456 [INFO] Cycle 1 complete: 1 symbol processed
2026-01-09 08:55:24.567 [INFO] Cycle 2 complete: 1 symbol processed
2026-01-09 09:05:25.678 [INFO] Cycle 3 complete: 1 symbol processed
...
```

### Every market data request, you should see:
```
2026-01-09 08:45:10.123 [INFO] Historical data fetch: SPY 60 bars
2026-01-09 08:45:11.234 [INFO] Strategy decision: HOLD (0.45 confidence)
```

### Never should you see:
```
❌ "GatewayCircuitBreaker OPEN" - indicates sustained failures
❌ "historical_data_timeout" - indicates data fetch failure
❌ "EBuffer overflow" - indicates subscription accumulation
❌ "Connection reset" - indicates Gateway disconnection
```

---

## Failure Scenarios & Recovery

### Scenario A: Timeout After 5 Minutes (Original Failure)
**Indicates**: Circuit breaker improvements didn't fully solve the issue

**Actions**:
1. Let it run to completion (will eventually stop after 4 hours)
2. Check logs for error patterns
3. Investigate: Are subscriptions still accumulating?
4. Consider: Need async cleanup or stronger rate limiting

### Scenario B: Circuit Breaker Enters OPEN
**Indicates**: Gateway is consistently unresponsive (3+ failures)

**What happens**:
- Bot skips cycles while circuit recovers (5-minute timeout)
- Logs show "GatewayCircuitBreaker OPEN: 3 consecutive failures"
- Bot resumes on next HALF_OPEN recovery attempt

**Expected behavior**: OPEN → wait 5 min → HALF_OPEN → test → CLOSED (success)

### Scenario C: Graceful Shutdown After 4 Hours
**Indicates**: Success! Phase 3 passed.

**Expected sequence**:
1. Timeout triggers after 14400 seconds (exactly 4 hours)
2. Bot catches timeout and starts graceful shutdown
3. Logs show final cycle summary
4. Process exits with status 0

---

## Post-Execution Analysis

### Step 1: Count Successful Cycles
```bash
# Count "cycle_complete" events
.venv\Scripts\python -c "
import json
with open('logs/bot.jsonl', 'r') as f:
    cycles = [json.loads(line) for line in f if 'cycle_complete' in line or 'Cycle' in str(line)]
    print(f'Total cycles: {len(cycles)}')
    print(f'First cycle: {cycles[0] if cycles else None}')
    print(f'Last cycle: {cycles[-1] if cycles else None}')
"
# Expected: 24-30 cycles (one every 10 minutes × 4 hours)
```

### Step 2: Check for Errors
```bash
# Count errors and warnings
.venv\Scripts\python -c "
import re
with open('logs/bot.log', 'r') as f:
    content = f.read()
    errors = len(re.findall(r'\[ERROR\]', content))
    warnings = len(re.findall(r'\[WARN', content))
    timeouts = content.count('historical_data_timeout')
    circuit_open = content.count('GatewayCircuitBreaker OPEN')
    print(f'Errors: {errors}')
    print(f'Warnings: {warnings}')
    print(f'Timeouts: {timeouts}')
    print(f'Circuit OPEN events: {circuit_open}')
"
# Expected (success):
# Errors: 0
# Warnings: 0-2 (only startup warnings expected)
# Timeouts: 0
# Circuit OPEN events: 0
```

### Step 3: Calculate Average Response Time
```bash
# Extract response times from logs
.venv\Scripts\python -c "
import re
import json
times = []
with open('logs/bot.jsonl', 'r') as f:
    for line in f:
        try:
            entry = json.loads(line)
            if 'duration_ms' in entry:
                times.append(entry['duration_ms'])
        except:
            pass

if times:
    print(f'Requests: {len(times)}')
    print(f'Min: {min(times):.0f}ms')
    print(f'Max: {max(times):.0f}ms')
    print(f'Avg: {sum(times)/len(times):.0f}ms')
"
# Expected (success):
# Min: 500-1000ms
# Max: 1500-2500ms
# Avg: 1000-1500ms
```

---

## Success Criteria Checklist

### ✅ Complete SUCCESS (proceed to Phase 4)
- [ ] Ran for 4+ hours without manual intervention
- [ ] 24+ complete cycles (at least 2+ hours)
- [ ] Zero "historical_data_timeout" errors
- [ ] Zero "GatewayCircuitBreaker OPEN" warnings
- [ ] Average response time < 2 seconds
- [ ] Memory stable (< 200MB)
- [ ] All 117 unit tests still passing

### ⚠️ Partial SUCCESS (investigate further)
- [ ] Ran for 30-120 minutes then timeout
- [ ] 3-12 complete cycles
- [ ] 1-2 "historical_data_timeout" errors
- [ ] Circuit breaker entered HALF_OPEN (not full OPEN)
- Action: Additional rate limiting needed

### ❌ FAILURE (revert to original)
- [ ] Timeout within first 5 minutes
- [ ] 0-2 cycles completed
- [ ] Repeated "historical_data_timeout" errors
- [ ] Circuit breaker entered OPEN state
- Action: Investigate alternative root causes

---

## Rollback (If Needed)

### Revert Code Changes
```bash
# Get commit before improvements
git log --oneline -10
# Find commits before ae8f70b

# Revert the improvements
git revert ae8f70b       # Revert circuit breaker
git revert 6ef3aa6      # Revert summary

# Or revert to specific commit
git reset --hard <commit-hash>  # Nuclear option

# Restore original settings
copy configs\settings.yaml.backup configs\settings.yaml
```

### Verify Rollback
```bash
# Confirm original code is active
type src\bot\scheduler.py | find "GatewayCircuitBreaker"
# Should return nothing (class removed)

# Run Phase 3 again with original code to confirm failure pattern
```

---

## Success Path (If Phase 3 Passes)

### Next Steps
1. **Document Results**: Create Phase 3 Success Report
2. **Run Phase 4**: 24-hour production dry-run with 5 symbols
3. **Prepare Phase 5**: Paper trading with real orders
4. **Plan Production**: Deploy to Raspberry Pi with monitoring

---

## Contact & Support

If Phase 3 fails or you encounter issues:
1. Check the detailed logs: `logs/bot.log` and `logs/bot.jsonl`
2. Review: [PHASE_3_IMPLEMENTATION_PLAN.md](PHASE_3_IMPLEMENTATION_PLAN.md)
3. Check: [EXTENDED_DRY_RUN_2026-01-07.md](EXTENDED_DRY_RUN_2026-01-07.md) for original failure pattern
4. Reference: [copilot-instructions.md](.github/copilot-instructions.md) for architecture

---

## Timeline Estimate

| Step | Duration | Notes |
|------|----------|-------|
| Prerequisites check | 5 min | Verify Gateway, Git, Python |
| Configuration setup | 5 min | Edit settings.yaml |
| Pre-launch tests | 10 min | Gateway + Circuit breaker + tests |
| **Phase 3 Execution** | **4 hours** | Main test run |
| Post-execution analysis | 10 min | Count cycles, check errors |
| **Total** | **~4.5 hours** | Real-time monitoring required |

---

**Status**: ✅ Ready to Execute  
**Expected Outcome**: 70-80% probability of success  
**Date**: 2026-01-09

Good luck! This is a critical test for bot reliability. 🎯

