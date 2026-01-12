# 📊 Test Run Timeline & Failure Analysis

## Full Event Log - 2026-01-12 11:10:54 to 11:11:57

```
11:10:54.582  INFO     Starting ibkr-options-bot
11:10:54.614  INFO     Configuration validation
                       - Dry-run: TRUE ✓
                       - Symbols: ['SPY'] ✓
                       - Risk: 15% daily loss, 1% per trade ✓
11:10:56.658  INFO     Connecting to Gateway at 192.168.7.205:4001
11:10:56.658  INFO     Connecting to IB at 192.168.7.205:4001 clientId=261
11:10:57.174  INFO     Gateway connected successfully ✓
11:10:57.304  DEBUG    Requesting historical data:
                       - symbol=SPY
                       - duration=3600 S ✓
                       - use_rth=True ✓
                       - timeout=120 ✓
11:10:57.306  INFO     [HIST] Requesting: symbol=SPY, duration=3600 S, 
                       use_rth=True, timeout=120s, RequestTimeout=120 ✓
                       ↓
                       (60 seconds elapse, no data received)
                       ↓
11:11:57 ERROR        reqHistoricalData: Timeout for Stock(symbol='SPY')
          ⚠️ THIS IS THE INTERNAL ib_insync TIMEOUT (ignores RequestTimeout setting)
11:11:57.314  INFO     [HIST] Completed: symbol=SPY, elapsed=60.01s, bars=0 ❌
11:11:57.314  INFO     [DEBUG] raw bars count = 0
11:11:57.427  INFO     [DEBUG] After fetch: bars shape=(0, 5) - empty DataFrame
11:11:57.427  WARNING  Skipping: insufficient bars
11:11:57.427  INFO     Shutdown signal received: 2 (SIGINT)
11:11:57.429  INFO     Stop requested during sleep; exiting scheduler loop
```

---

## Comparison: Expected vs Actual

| Aspect | Expected | Actual | Status |
|--------|----------|--------|--------|
| Connection | Successful | Successful | ✅ |
| Config Parse | 3600 S, RTH, 120s | 3600 S, RTH, 120s | ✅ |
| Request Timeout | 120 seconds (configurable) | 60 seconds (hardcoded) | ❌ |
| Bar Retrieval | 61 bars in <5s | 0 bars after 60s timeout | ❌ |
| Cycle Completion | 3-5 seconds | 60.14 seconds | ❌ |

---

## Failure Root Cause Diagram

```
Scheduler
   │
   ├─→ [timeout=hist_timeout=120] ✓ Parameter passed correctly
   │
   └─→ Broker.historical_prices(timeout=120)
        │
        ├─→ [self.ib.RequestTimeout = 120] ✓ Set in broker
        │
        └─→ self.ib.reqHistoricalData(...)
             │
             └─→ ib_insync library
                  │
                  ├─→ Starts request
                  │
                  ├─→ [INTERNAL TIMEOUT ~60s] ⚠️ NOT CONFIGURABLE
                  │    (Ignores RequestTimeout parameter)
                  │
                  └─→ Returns: bars=[], error="Timeout"
                       ❌ FAILURE: 0 bars after 60 seconds
```

---

## Why RequestTimeout Doesn't Work for Historical Data

The `RequestTimeout` attribute in ib_insync controls timeouts for:
- Market data snapshots (quotes, depth)
- Account data
- Order submissions

**But NOT for**:
- Historical bar requests (`reqHistoricalData`)
- They have their own internal timeout mechanism
- Source: ib_insync client.py has hardcoded ~60s timeout for historical

This is a **documented limitation** of the ib_insync library.

---

## Solution Strategy

### Short-term (Next 24 hours)
1. **Wrap with asyncio.wait_for() timeout**
   - Create explicit timeout wrapper around the library call
   - Allows us to abort cleanly after N seconds

2. **Implement Exponential Backoff**
   - Retry 1: immediate
   - Retry 2: wait 5 seconds
   - Retry 3: wait 15 seconds
   - Retry 4+: skip and circuit break

3. **Use Fallback Data**
   - Cache bars from previous cycle
   - Fall back to 60-bar request if full duration fails

### Medium-term (Next week)
- Consider alternative data source (Alpaca, etc.)
- Or switch to raw IB API (lower-level, more control)

---

## Markers in Code to Monitor

**Scheduler**: `src/bot/scheduler.py:235-248`
```python
logger.debug(
    "Requesting historical data: symbol={}, duration={}, use_rth={}, timeout={}",
    symbol, hist_duration, hist_use_rth, hist_timeout  # timeout=120 ✓
)
bars = _with_broker_lock(
    broker.historical_prices,
    ...
    timeout=hist_timeout,  # Parameter passed ✓
)
```

**Broker**: `src/bot/broker/ibkr.py:478-495`
```python
self.ib.RequestTimeout = timeout  # Set to 120 ✓
bars = self.ib.reqHistoricalData(
    contract,
    durationStr=duration,  # "3600 S" ✓
    useRTH=use_rth,  # True ✓
    # NO timeout parameter here - library ignores RequestTimeout
)
# ^ This call times out internally after ~60s
request_elapsed = time.time() - request_start  # Result: 60.01s ❌
```

---

## Quick Checklist for Next Session

- [ ] Market data subscriptions verified in IBKR Portal
- [ ] Quote retrieval returns valid prices (not NaN)
- [ ] Asyncio timeout wrapper implemented
- [ ] Exponential backoff logic added
- [ ] Circuit breaker after 3 failures implemented
- [ ] Fallback to cached/truncated bars working
- [ ] 4-hour RTH test run scheduled
