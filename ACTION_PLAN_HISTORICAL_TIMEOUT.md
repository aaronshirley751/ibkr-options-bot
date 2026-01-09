# Action Plan: Fix Historical Data Timeouts

**Objective**: Resolve the 4+ historical data timeouts that activate circuit breaker backoff

**Root Cause**: `reqHistoricalData` is timing out during market hours (likely hitting ib_insync's ~30s default timeout)

**Solution**: Add explicit longer timeout to historical_prices() method

---

## Code Changes Required

### File: `src/bot/broker/ibkr.py`

**Change Location**: Lines 445-485 (historical_prices method)

**Current Code**:
```python
def historical_prices(
    self,
    symbol: str,
    duration: str = "3600 S",
    bar_size: str = "1 min",
    what_to_show: str = "TRADES",
    use_rth: bool = True,
):
```

**Proposed Change**: Add `timeout: int = 60` parameter and use it

```python
def historical_prices(
    self,
    symbol: str,
    duration: str = "3600 S",
    bar_size: str = "1 min",
    what_to_show: str = "TRADES",
    use_rth: bool = True,
    timeout: int = 60,  # <-- ADD THIS LINE
):
```

**Then in the method body**, wrap the `reqHistoricalData` call with timeout:

At line ~477, change:
```python
bars = self.ib.reqHistoricalData(
    contract,
    endDateTime="",
    durationStr=duration,
    barSizeSetting=bar_size,
    whatToShow=what_to_show,
    useRTH=use_rth,
    formatDate=1,
)
```

To:
```python
# Use explicit timeout for market hours; ib_insync default is ~30s which can timeout
# during high Gateway load. 60s is conservative and still fast enough for trading.
self.ib.RequestTimeout = timeout
try:
    bars = self.ib.reqHistoricalData(
        contract,
        endDateTime="",
        durationStr=duration,
        barSizeSetting=bar_size,
        whatToShow=what_to_show,
        useRTH=use_rth,
        formatDate=1,
    )
finally:
    # Reset to default (10s) for other operations
    self.ib.RequestTimeout = 10
```

---

## Why This Works

1. **ib_insync allows setting `RequestTimeout`** on the IB instance
2. **60 seconds is conservative** — still fast enough for trading decisions
3. **Default is ~10 seconds** for general requests, 30-60s for historical data isn't unreasonable during heavy load
4. **We reset it** so other operations (market data, options chain) keep their reasonable timeouts

---

## Testing Plan

### Test 1: Code Verification
```bash
grep -A 5 "RequestTimeout\|timeout:" src/bot/broker/ibkr.py | head -20
```

### Test 2: Unit Tests
```bash
pytest tests/ -v
```
Should still pass all 117 tests.

### Test 3: Live Test (30+ minutes)
```bash
# Stop any running bot
pkill -f "python -m src.bot.app"

# Apply fix to code
# (we'll do this next)

# Run bot
.venv/Scripts/python.exe -m src.bot.app

# Monitor
tail -f logs/bot.log | grep -E "Cycle complete|Timeout|backoff"
```

**Success Criteria**:
- ✓ No "Historical data unavailable 3 times" warnings
- ✓ No circuit breaker backoff activations
- ✓ Cycles execute every 600s (10 min) consistently
- ✓ Cycle times: 0.5-5 seconds (not 33-60s)

---

## Alternative Solutions (if Option A doesn't work)

### Option B: Reduce Request Load
```python
# In configs/settings.yaml or directly in scheduler
# Reduce frequency or bar window
schedule:
  interval_seconds: 900  # 15 min instead of 10 min
```

### Option C: Use Non-RTH (Extended Hours) Data
```python
use_rth: False  # Allows requests during lower-load extended hours window
```

### Option D: Reduce Bars Requested
```python
duration: "1800 S"  # 30 min instead of 60 min
```

---

## Implementation Decision

**Recommended**: Apply Option A (increase timeout to 60s) immediately
- Low risk (just a timeout value)
- No code logic changes
- Addresses the direct cause
- If logs still show timeouts after this, we know it's Gateway-side issue

**Fallback**: Option B (reduce interval to 900s) if Option A doesn't help

---

## Success Expected

Based on logs, the pattern is:
- First 5-6 cycles work fine (~3s each)
- Then timeouts start (60s pattern)
- Circuit breaker activates
- Long wait period

With 60s timeout on historical data requests, the Gateway should have enough time to respond, and the 60s "slow" cycles should become ~3-5s normal cycles.

**Target**: Get bot to run 30+ minutes with **all cycles < 10 seconds**, zero backoff activations.

---

## Next Command

Once you confirm this approach, run:
```bash
# Show current timeout handling
grep -n "RequestTimeout" src/bot/broker/ibkr.py
```

If not present, we'll add it. If present, we'll increase the value.

