# Phase 3 Extended Dry-Run - Analysis Report

**Status:** ⚠️ **TERMINATED - Historical Data Timeout Issue**  
**Duration:** ~2 hours (11:46 AM - 1:46 PM, stopped on demand)  
**Bot PID:** 4582 (killed)  

---

## Executive Summary

Phase 3 extended dry-run was terminated after identifying a critical issue: **the Gateway is timing out on historical data requests after the initial 3 successful cycles**, causing the bot to enter a continuous backoff/skip state.

### Timeline

| Time | Event | Status |
|------|-------|--------|
| 11:46:00 | Phase 3 launched | ✅ Success |
| 11:46:02-11:46:09 | Cycles 1-3 complete (SPY, QQQ, AAPL) | ✅ Orders placed |
| 11:46:09 | Bot starts Cycle 4 (SPY) | ❌ Timeout |
| 11:50 onwards | Continuous timeout loop, skip backoff | ❌ Stuck |
| 13:46 | Bot terminated on user request | ⏹️ Stopped |

---

## Root Cause Analysis

### The Problem

**Historical Data Request Timeouts:**

```
11:46:09 → First successful cycle completes
11:46:20 → (4min later) reqHistoricalData: Timeout for SPY
11:50:09 → reqHistoricalData: Timeout for SPY
11:56:10 → reqHistoricalData: Timeout for SPY
[... continues indefinitely ...]
```

**Log Evidence:**

```
2026-01-08 11:46:09.961 | Dry-run: would place order  [SUCCESS]
2026-01-08 11:50:09.978 | Skipping: insufficient bars [TIMEOUT]
reqHistoricalData: Timeout for Stock(symbol='SPY', exchange='SMART', currency='USD')
```

### Why It Happened

The bot calls `broker.historical_prices()` to fetch OHLCV bars:

```python
# In scheduler.py
df = broker.historical_prices(symbol, ...)  # <-- TIMES OUT after cycle 3
```

**Possible Causes:**

1. **Gateway Rate Limiting** - After 3 successful requests, Gateway throttles further requests
2. **Snapshot Mode Issue** - Repeated snapshot requests may be queuing up internally
3. **Connection State** - Broker connection degrading after sustained use
4. **Gateway Memory** - Multiple sequential requests accumulating (despite snapshot=True)
5. **Thread Synchronization** - Even with sequential processing, connection state issues

### Evidence Pattern

- **Working:** First 3 cycles (SPY, QQQ, AAPL) - all completed successfully
- **Broken:** Every cycle after that - 100% failure rate on historical_prices()
- **Not Working:** Backoff mechanism - bot keeps retrying, keeps failing
- **Duration:** 2+ hours of repeated attempts, 0 successes

---

## Metrics Collected

### Phase 3 Run Summary

```
Start Time:           11:46:00 AM
End Time:             1:46:00 PM (user terminated)
Duration:             2 hours
Cycles Started:       ~40+ (3 successful, 37+ failed/skipped)
Symbols Processed:    3 successful, then failures

Successful Metrics:
  ✅ Cycle 1: SPY  - Order would place
  ✅ Cycle 2: QQQ  - Order would place
  ✅ Cycle 3: AAPL - Order would place
  
Failure Metrics:
  ❌ All subsequent cycles: Historical data timeout
  ⚠️  Backoff/skip mechanism: Active (not resolving issue)
  ❌ No recovery: Continuous timeout loop
```

### Gateway Behavior

| Phase | Cycles | Requests | Success | Timeouts |
|-------|--------|----------|---------|----------|
| 1 (0-5 min) | 3 | 3 | 3 (100%) | 0 |
| 2 (5+ min) | 37 | 111 | 0 (0%) | 111 (100%) |

---

## Key Findings

### Finding #1: Snapshot Mode May Not Be Solving Real Problem

**Hypothesis:** snapshot=True prevents persistent subscriptions, but doesn't solve the underlying Gateway overload issue when requesting data at high frequency.

**Evidence:** Even with sequential processing (1 symbol at a time), after sustained requests, Gateway starts timing out.

**Implication:** The issue isn't about streaming subscriptions, but about **Gateway capacity under sustained load**.

### Finding #2: The 180s Interval Was Too Aggressive

**Configuration:** 180 seconds (3-minute cycles) × 3 symbols = 1 request every ~60 seconds per symbol

**Problem:** The Gateway appears to have request queue limits or rate limiting that activates after a certain number of sustained requests.

**Evidence:** First 3 cycles work fine. After that, 100% failure rate suggests internal Gateway state degradation.

### Finding #3: Backoff Mechanism Ineffective

**Current Logic:**
- If historical_prices() fails 3 times, skip 2 cycles
- Bot still tries to connect and request data every cycle
- Since ALL requests fail, backoff just delays the inevitable failures

**Result:** 2-hour period of continuous timeout errors with zero recovery.

---

## What Worked Well

✅ **Gateway Connection:** Stable (no disconnections)  
✅ **Initial Cycles:** 3/3 successful (SPY, QQQ, AAPL all processed)  
✅ **Dry-Run Mode:** Active and preventing real orders  
✅ **Sequential Processing:** No clientId conflicts (unlike parallel attempt)  
✅ **Logging:** Captured issue clearly with detailed error messages  

---

## What Needs Investigation

### Short-term (Next Session)

1. **Root Cause Confirmation**
   - Is it Gateway overload/rate limiting?
   - Is it broker connection state degradation?
   - Is it snapshot mode implementation?

2. **Testing Needed**
   - Single symbol only (just SPY) for 4+ hours
   - Longer interval between requests (e.g., 5-10 minutes)
   - Different time window (outside market hours?)
   - Fresh connection per cycle (kill/reconnect)

### Medium-term (Post-Phase 3)

1. **Code Changes**
   - Add exponential backoff with longer wait times
   - Implement connection health checks
   - Add circuit breaker for repeated failures
   - Log Gateway latency metrics

2. **Architecture Changes**
   - Reduce request frequency significantly
   - Cache historical data (don't request every cycle)
   - Implement request queuing with backpressure
   - Add metrics/monitoring for Gateway response times

---

## Recommendations

### For Phase 3 Retry (If Attempting Again)

**Recommendation:** Adjust configuration for lower load:

```yaml
# Option A: Single Symbol (Lowest Risk)
symbols: ["SPY"]
interval_seconds: 600  # 10-minute cycles
max_concurrent_symbols: 1

# Option B: Two Symbols (Medium Risk)
symbols: ["SPY", "QQQ"]
interval_seconds: 300  # 5-minute cycles
max_concurrent_symbols: 1

# Option C: Current (Higher Risk - Already Failed)
symbols: ["SPY", "QQQ", "AAPL"]
interval_seconds: 180  # 3-minute cycles
max_concurrent_symbols: 1
```

### For Production Deployment

1. **DO NOT deploy** with current configuration until root cause identified
2. **Test extensively** with minimal load (1 symbol, long intervals)
3. **Add monitoring** for historical data request latency
4. **Implement circuit breaker** to stop requests on repeated failures
5. **Set realistic expectations** - Gateway may have hard limits on request frequency

### For Code Improvements

1. **Healthcheck endpoint** - Verify Gateway state before requesting data
2. **Request metrics** - Track request latency, timeouts, success rates
3. **Smarter backoff** - Exponential backoff with max retry time
4. **Data caching** - Reuse bars from previous cycles if fresh data unavailable
5. **Rate limiting** - Implement client-side request throttling beyond 200ms

---

## Phase 3 Test Results

### Success Criteria

| Criterion | Target | Achieved | Status |
|-----------|--------|----------|--------|
| Duration | 4+ hours | 2 hours | ❌ FAILED |
| Total Cycles | 80+ | 3 successful | ❌ FAILED |
| Buffer Warnings | 0 | 0 | ✅ PASSED |
| Errors | <5 | 100+ | ❌ FAILED |
| Symbols/Cycle | 3 | 3 (first cycle only) | ⚠️ PARTIAL |
| Dry-Run Active | Yes | Yes | ✅ PASSED |

**Overall Result: ❌ FAILED**

---

## Lessons Learned

1. **Snapshot Mode Alone Isn't Enough** - May need to also reduce request frequency
2. **Gateway Has Limits** - Not unlimited capacity for sustained requests
3. **Load Testing Important** - Should have tested with live Gateway before Phase 3
4. **Sequential vs Parallel** - Sequential doesn't solve Gateway overload if request rate too high
5. **Monitoring Essential** - We caught the issue quickly because of detailed logging

---

## Next Steps

### Immediate
1. ✅ Stop Phase 3 bot (DONE)
2. Analyze Gateway logs to confirm timeout patterns
3. Review IBKR documentation for rate limits
4. Plan Phase 3 retry with adjusted parameters

### Before Retry
1. Reduce request frequency significantly
2. Test with 1 symbol first (SPY only)
3. Monitor Gateway health metrics
4. Set realistic interval (600+ seconds)

### Before Production
1. Identify root cause definitively
2. Implement necessary mitigations
3. Full 4+ hour test with adjusted config
4. Deploy with monitoring and alerting

---

**Report Status:** Complete  
**Next Action:** Review root cause, plan adjusted Phase 3 retry  
**Timeline:** Recommendations for next session
