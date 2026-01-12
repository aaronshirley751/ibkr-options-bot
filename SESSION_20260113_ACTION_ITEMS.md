# 🎯 IMMEDIATE ACTIONS - Session 2026-01-13 Starts Here

## Priority 1: Verify Market Data Subscriptions (URGENT - Next 1 Hour)

### Step 1.1: Check IBKR Account Settings
```
1. Go to https://www.interactivebrokers.com/portal
2. Login with your credentials
3. Navigate to: Account Management → Account Settings → User Settings
4. Find: Market Data Subscriptions
5. Check status of:
   ✓ US Securities Snapshot & Futures OneExchange (US) - should be ACTIVE
   ✓ US Securities - Level 2 (should be ACTIVE for options)
   ✓ Look for any expired subscriptions
6. Screenshot or note any issues found
```

### Step 1.2: Run Connectivity Test
```bash
cd "c:\Users\tasms\my-new-project\Trading Bot\ibkr-options-bot"
.venv/Scripts/python.exe test_ibkr_connection.py \
  --host 192.168.7.205 \
  --port 4001 \
  --client-id 350 \
  --timeout 30
```

**Expected Output**:
```
{'event': 'stock_snapshot', 'symbol': 'SPY', 'last': 485.23, 'bid': 485.20, 'ask': 485.25}
{'event': 'option_snapshot', 'ok': True, 'contracts': 5, ...}
```

**If Output Shows NaN**:
```
{'event': 'stock_snapshot', 'symbol': 'SPY', 'last': nan, 'bid': nan, 'ask': nan}  ❌
```
→ Proceed to Step 1.3

### Step 1.3: If NaN Persists - Contact IBKR Support
```
Subject: Market data quotes returning NaN via API/Gateway

Description:
- Account: [your account number]
- Issue: Stock quotes returning NaN when querying via IB Gateway
- Tools used: ib_insync library with paper trading account
- Subscriptions status: [from Step 1.1]
- Test timestamp: [current timestamp]
- Test command: test_ibkr_connection.py with output

Request: Please verify API access level and market data entitlements
```

**Support Link**: https://www.interactivebrokers.com/en/support/

---

## Priority 2: Implement Timeout Workaround (TODAY - 4 Hours)

### Step 2.1: Create Asyncio Timeout Wrapper

**File**: `src/bot/broker/ibkr.py`

**Location**: Around line 460, before `historical_prices()` method

**Add this helper method**:
```python
def _fetch_bars_async(self, contract, **kwargs) -> list:
    """Fetch historical bars with explicit asyncio timeout."""
    import asyncio
    
    async def fetch():
        # reqHistoricalDataAsync is available in ib_insync
        if not hasattr(self.ib, 'reqHistoricalDataAsync'):
            # Fallback for older versions - use reqHistoricalData
            return self.ib.reqHistoricalData(contract, **kwargs)
        return await self.ib.reqHistoricalDataAsync(contract, **kwargs)
    
    try:
        # Run with explicit timeout (our override)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        bars = loop.run_until_complete(
            asyncio.wait_for(fetch(), timeout=self.timeout)
        )
        return bars
    except asyncio.TimeoutError:
        logger.error(f"Timeout fetching bars for {contract.symbol} after {self.timeout}s")
        return []
    finally:
        loop.close()
```

### Step 2.2: Add Exponential Backoff Retry Logic

**File**: `src/bot/scheduler.py`

**Location**: In `process_symbol()` function, around line 230

**Add this before the historical_prices call**:
```python
# Track consecutive timeouts per symbol
_historical_timeout_counts = {}  # Symbol -> timeout count
_historical_timeout_threshold = 3

# Implement exponential backoff retry
retry_delays = [0, 5, 15]  # immediate, 5s, 15s
bars = None
for retry_idx, delay in enumerate(retry_delays):
    if delay > 0:
        logger.info(f"Retry {retry_idx} for {symbol}: waiting {delay}s")
        time.sleep(delay)
    
    try:
        bars = _with_broker_lock(
            broker.historical_prices,
            symbol,
            duration=hist_duration,
            bar_size=hist_bar_size,
            what_to_show=hist_what,
            use_rth=hist_use_rth,
            timeout=hist_timeout,
        )
        if bars is not None and len(bars) > 0:
            _historical_timeout_counts[symbol] = 0  # Reset count on success
            break  # Success - exit retry loop
    except (TimeoutError, Exception) as e:
        logger.debug(f"Historical data fetch failed (retry {retry_idx}): {type(e).__name__}")
        if retry_idx == len(retry_delays) - 1:  # Last retry
            _historical_timeout_counts[symbol] = _historical_timeout_counts.get(symbol, 0) + 1
        continue
```

### Step 2.3: Add Circuit Breaker After 3 Failures

**Location**: Right after the retry loop (around line 260)

**Add this**:
```python
# Circuit breaker: skip symbol after 3 consecutive timeout failures
if _historical_timeout_counts.get(symbol, 0) >= 3:
    logger.warning(
        f"Circuit breaker OPEN for {symbol}: {_historical_timeout_counts[symbol]} "
        f"consecutive timeouts. Skipping this symbol for 10 cycles."
    )
    # Could add a cooldown mechanism here
    continue  # Skip to next symbol
```

### Step 2.4: Add Fallback to Cached Bars

**Location**: Right after the retry loop (around line 265)

**Add this**:
```python
# Fallback: use cached bars from previous cycle if recent enough
if bars is None or len(bars) == 0:
    logger.info(f"No fresh bars for {symbol}, checking cache...")
    
    # Check if we have cached bars from previous cycle
    if symbol in _symbol_bar_cache:
        cached_bars, cache_time = _symbol_bar_cache[symbol]
        age_seconds = time.time() - cache_time
        
        if age_seconds < 300:  # Less than 5 minutes old
            logger.info(f"Using cached bars for {symbol} (age: {age_seconds:.0f}s)")
            bars = cached_bars
        else:
            logger.info(f"Cached bars too old for {symbol} ({age_seconds:.0f}s), skipping")
            bars = None
    else:
        logger.info(f"No cache for {symbol}, will skip this cycle")
        bars = None

# Cache the bars for next cycle
if bars is not None and len(bars) > 0:
    _symbol_bar_cache[symbol] = (bars, time.time())
```

**At top of scheduler.py**, add:
```python
_symbol_bar_cache = {}  # Symbol -> (bars, timestamp)
```

---

## Priority 3: Validation Test (TOMORROW - 30 Minutes)

Once priorities 1 & 2 are complete:

```bash
cd "c:\Users\tasms\my-new-project\Trading Bot\ibkr-options-bot"

# Run connectivity test first
.venv/Scripts/python.exe test_ibkr_connection.py \
  --host 192.168.7.205 \
  --port 4001 \
  --client-id 355 \
  --timeout 30

# If quotes are valid (not NaN), run bot test
.venv/Scripts/python.exe -m src.bot.app

# Monitor logs for:
# - [HIST] Requesting and Completed lines
# - "Cycle complete" messages (should show 3-5 second cycles, not 60+)
# - No timeout errors
# - Successful bar counts (expect 30-60+ bars per request)
```

**Success Criteria**:
- ✅ Quotes returning valid prices (not NaN)
- ✅ No "Timeout" errors in logs
- ✅ Cycle times 3-10 seconds (not 60+)
- ✅ Bar retrieval working
- ✅ Runs for 30+ minutes without reconnection issues

---

## Testing Checklist

Before moving to 4-hour production readiness test:

**Market Data** (Priority 1):
- [ ] IBKR subscriptions verified as ACTIVE
- [ ] test_ibkr_connection.py returns valid quotes (not NaN)
- [ ] Option chain data available (not no_secdef)

**Code Changes** (Priority 2):
- [ ] Asyncio timeout wrapper implemented
- [ ] Exponential backoff retry added
- [ ] Circuit breaker logic in place
- [ ] Fallback to cached bars working
- [ ] Code syntax validated (no import errors)

**Functional Testing** (Priority 3):
- [ ] Bot starts without errors
- [ ] First cycle completes in <10 seconds
- [ ] Logs show "Cycle complete: 1 symbols in Xs"
- [ ] No timeout errors in 30+ minute run
- [ ] No reconnection issues during test

---

## Files to Reference

**Session 2026-01-12 Documentation**:
- [SESSION_20260112_EXECUTIVE_SUMMARY.md](SESSION_20260112_EXECUTIVE_SUMMARY.md) - High-level overview
- [SESSION_20260112_ANALYSIS.md](SESSION_20260112_ANALYSIS.md) - Detailed action plan
- [SESSION_20260112_START_HERE.md](SESSION_20260112_START_HERE.md) - Quick reference

**Code Files to Modify**:
- `src/bot/broker/ibkr.py` - Add asyncio timeout wrapper
- `src/bot/scheduler.py` - Add backoff retry, circuit breaker, cache fallback

**Test Logs**:
- `logs/session_20260112_test.log` - Shows 60s timeout failure
- `logs/bot.log` - Detailed bot execution log

---

## Success Metrics

| Metric | Target | Current |
|--------|--------|---------|
| Market Data Availability | Valid quotes | NaN |
| Historical Data Timeout | 90s (or fail gracefully) | 60s hard timeout |
| Cycle Duration | 3-10 seconds | 60 seconds |
| Uptime | 4+ hours | 1 minute |
| Bar Retrieval Success | 95%+ | 0% |

---

**Status**: Ready for next session  
**Estimated Time to Complete**: 6-8 hours total (1h urgent + 4h code + 1h testing + buffer)  
**Next Major Milestone**: 4-hour production readiness test
