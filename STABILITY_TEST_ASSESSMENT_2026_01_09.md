# Stability Test Assessment: Extended Run 2026-01-09

**Test Duration**: ~35 minutes (11:28-12:03 EST)  
**Client ID**: 260 (fresh)  
**Configuration**: SPY only, 600s interval, dry_run=true  
**Status**: COMPLETED - Issues Identified

---

## Executive Summary

The stability test revealed a **critical regression** after the DataFrame fix. While the first 2 cycles executed successfully with full data (121 bars each, 3.15-3.27s), subsequent cycles experienced repeated timeouts on 2-hour historical data requests.

**Key Finding**: The timeout fix (60s) is insufficient for 2-hour requests when the scheduler escalates from 1-hour to 2-hour bars.

---

## Test Results

### Cycle Performance

| Cycle | Time | Duration | Status | Bars | Notes |
|-------|------|----------|--------|------|-------|
| **1** | 11:28:59 | 3.15s | ✅ SUCCESS | 121 | Initial - 1hr bars, full data |
| **2** | 11:30:31 | 3.27s | ✅ SUCCESS | 121 | First scheduled cycle, full data |
| **3** | 11:41:31 | 60.02s | ⚠️ TIMEOUT | 0 | 2-hour bars request → timeout |
| **4** | 11:52:31 | 60.02s | ⚠️ TIMEOUT | 0 | 2-hour bars request → timeout |
| **5** | 12:03:31 | 60.02s | ⚠️ TIMEOUT | 0 | 2-hour bars request → timeout |

**Pattern**: 
- Cycles 1-2: Fast, data available, processing succeeds
- Cycles 3-5: Request extended timeouts (60s), return 0 bars, skip processing

---

## Root Cause: Scheduler Request Escalation

Looking at the error logs, the scheduler is making **two different requests** per symbol:

**Cycle 1-2** (RTH=True, 1-hour window):
```
duration='3600 S', bar_size='1 min', use_rth=True
→ Returns 121 bars in <1 second
→ Cycle completes in 3.15s
```

**Cycle 3-5** (RTH=False, 2-hour window):
```
duration='7200 S', bar_size='1 min', use_rth=False
→ Times out after 60 seconds (RequestTimeout=60)
→ Returns 0 bars
→ Cycle takes 60.02s
```

**Why the escalation?**
- Initial requests use RTH=True (regular trading hours), narrower window
- Scheduler logic escalates to RTH=False (any time) with longer duration after initial failures
- 2-hour of 1-minute bars (120 bars) is heavier load than 1-hour (60 bars)
- Gateway takes >60s to respond under this load

---

## Evidence from Logs

**Successful cycle (11:28:59)**:
```
[DEBUG] historical_prices(SPY): raw bars count = 121
[DEBUG] First bar: date=2026-01-09 10:28:00-05:00, close=693.18
[DEBUG] Last bar: date=2026-01-09 12:28:00-05:00, close=694.33
[DEBUG] Converted to rows: 121 rows
[DEBUG] DataFrame created: shape=(121, 6)
[DEBUG] After fetch: bars type=DataFrame, is_df=True, df_shape=(121, 5)
[INFO] Cycle decision
[INFO] Cycle complete: 1 symbols in 3.15s
```

**Failed cycle (11:41:31)**:
```
[ERROR] historical_prices failed for %s
TimeoutError: asyncio.exceptions.CancelledError
→ Request duration='7200 S' (2 hours)
→ Timeout after 60s
→ Bars returned = 0
[DEBUG] After fetch: bars type=DataFrame, is_df=True, df_shape=(0, 5)
[INFO] Skipping: insufficient bars
[INFO] Cycle complete: 1 symbols in 60.02s
```

---

## Circuit Breaker Status

**3 consecutive timeouts** triggered circuit breaker on cycle 5:
```
2026-01-09 12:03:31.958 | WARNING | src.bot.scheduler:process_symbol:320 
- Historical data unavailable 3 times; entering backoff (skip 2 cycles)
```

Would have skipped next 2 cycles (12:13, 12:23) if test continued.

---

## Impact Assessment: Recent Code Changes

### What Worked
✅ **DataFrame fix (was critical)**: Resolved the ValueError bug in scheduler.py line 272  
✅ **Debug logging**: Data flow tracking correctly shows 121 bars available  
✅ **Connection stability**: Fresh client_id=260 connected and reconnected smoothly  
✅ **Initial cycles**: Successfully processed options, made decisions  

### What Failed
❌ **Timeout handling for extended requests**: 60s timeout insufficient for 2-hour bars  
❌ **Request escalation strategy**: Scheduler escalates to longer durations that exceed timeout  
❌ **Gateway performance under load**: 2-hour requests taking >60s after 10+ minutes of operation  

---

## Key Observations

### 1. Two-Stage Request Pattern
The scheduler appears to have a fallback strategy:
- **Stage 1**: Request recent 1-hour data (RTH=True) → Fast, reliable
- **Stage 2** (if Stage 1 fails?): Request extended 2-hour data (RTH=False) → Slow, times out

Timeline suggests escalation happens around minute 11-12 of operation.

### 2. RequestTimeout Bug
The error stack shows:
```
timeout=self.ib.RequestTimeout  # Line 318 in ib.py
return util.run(*awaitables, timeout=self.ib.RequestTimeout)
```

**Critical bug**: The timeout was being **set to 0** in some path, overriding our 60s setting!
```
timeout=0  # Shown in error trace
```

This means the fix applied (timeout: int = 60 parameter) is **not being used** in the escalation path.

### 3. Gateway Behavior
- Initial requests complete in <1s (121 bars in 0.4s)
- After ~11 minutes of polling, Gateway response time increases dramatically
- 2-hour requests taking >60s suggests either:
  - Gateway cache/state issue
  - Rate limiting by IBKR
  - ib_insync library not properly passing timeout parameter

---

## Recommendations (Priority Order)

### CRITICAL (Must fix before next test)

**1. Fix timeout parameter propagation**
- The timeout=60 parameter is being ignored in escalated requests
- Verify historical_prices() is being called with timeout parameter in all code paths
- Check scheduler.py line 233-241 to see if timeout parameter is passed
- Current: `bars = _with_broker_lock(broker.historical_prices, symbol, ...)`
- May need: `bars = _with_broker_lock(broker.historical_prices, symbol, timeout=90, ...)`

**2. Increase timeout for extended requests**
- If 2-hour requests are necessary, timeout needs to be 120-180s minimum
- Or disable RTH=False requests and stick to RTH=True (1-hour) exclusively
- Or reduce bar_size to '5 mins' to reduce payload

**3. Investigate RequestTimeout=0 bug**
- Why is RequestTimeout showing as 0 in error trace when we set it to 60?
- May be timing issue: old_timeout reset happening before request completes
- May be separate timeout in ib_insync override

### HIGH (Should address)

**4. Reduce request frequency during backoff**
- Circuit breaker skips 2 cycles but bot still running
- Add exponential backoff: skip 5, 10, 20 cycles progressively
- Or pause entire run for 5+ minutes after 3 consecutive failures

**5. Monitor Gateway state**
- First 2 cycles: <1s per request
- Cycles 3-5: >60s per request
- Something changes after ~11 minutes
- Log Gateway response times and request queue depth

### MEDIUM (Next iteration)

**6. Add adaptive request strategy**
- If timeout occurs, fall back to shorter time window (1-hour instead of 2-hour)
- Track per-symbol what works and what times out
- Avoid RTH=False requests if RTH=True is sufficient

---

## Stability Assessment

| Criteria | Status | Notes |
|----------|--------|-------|
| **Data Availability** | ⚠️ DEGRADED | Works initially, fails after 11 min of operation |
| **Cycle Consistency** | ⚠️ INCONSISTENT | 3.15s, 3.27s, 60s, 60s, 60s - regression pattern |
| **Error Handling** | ✅ WORKING | Circuit breaker activated correctly |
| **Connection Stability** | ✅ STABLE | Client connect/reconnect working smoothly |
| **DataFrame Processing** | ✅ FIXED | No longer crashes on empty DataFrames |
| **Ready for Phase 3** | ❌ NO | Timeout handling regression blocks deployment |

---

## Code Changes Required

### File: src/bot/scheduler.py (lines 233-241)

Current (missing timeout parameter):
```python
bars = _with_broker_lock(
    broker.historical_prices,
    symbol,
    duration=hist_duration,
    bar_size=hist_bar_size,
    what_to_show=hist_what,
    use_rth=hist_use_rth,
)
```

Proposed fix:
```python
bars = _with_broker_lock(
    broker.historical_prices,
    symbol,
    duration=hist_duration,
    bar_size=hist_bar_size,
    what_to_show=hist_what,
    use_rth=hist_use_rth,
    timeout=120,  # Increased for extended requests
)
```

### File: src/bot/broker/ibkr.py (line 475)

Verify timeout parameter is being used:
```python
# Current line 475 - check if timeout is actually applied
bars = self.ib.reqHistoricalData(
    contract,
    endDateTime="",
    durationStr=duration,
    barSizeSetting=bar_size,
    whatToShow=what_to_show,
    useRTH=use_rth,
    formatDate=1,
)
# ^^^ This should be using the timeout parameter set on line 474
```

---

## Next Steps

1. **Stop the bot** ✅ (Done)
2. **Review timeout handling code** (Identify RequestTimeout=0 issue)
3. **Apply timeout parameter fix** (Ensure 120s timeout for extended requests)
4. **Add logging** (Log RequestTimeout value before/after requests)
5. **Restart test** (Should see consistent <10s cycles if fixed)
6. **Extended 60-minute run** (Verify no degradation over time)

---

## Session Context

- **Previous Issue**: DataFrame truthiness bug in scheduler.py → FIXED
- **New Issue**: Timeout parameter not propagated to escalated requests
- **Data Source**: Gateway proven working (test_direct_bars.py returns 61 bars)
- **Fix Status**: Code change required, estimated 15-30 min to implement and test
- **Impact**: Blocks Phase 3 deployment until timeout regression resolved

---

## Conclusion

The recent DataFrame fix was **critical and successful** - it resolved the false "insufficient bars" errors. However, a timeout handling regression has emerged when the scheduler escalates to longer-duration requests.

**The bot is now working for short requests but failing on extended historical data pulls.** This is a Gateway load issue, not a market data issue. 

With timeout parameter fixes, expect to see:
- All cycles complete in 3-10 seconds (not 60+)
- No circuit breaker activations
- Consistent data availability
- Ready for Phase 3 production testing

Estimated fix time: 30 minutes (code review, 1 change, test).
