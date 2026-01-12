# ⚡ QA AUDIT - QUICK START GUIDE
## 3 Critical Fixes to Deploy (6-8 hours total)

---

## THE PROBLEM
- ✗ Historical data times out at 60s (library limitation)
- ✗ Market data returning NaN (subscription issue)
- ✗ No retry logic on failures (immediate circuit break)
- **Result:** Bot can't get bars, can't trade

---

## THE SOLUTION (3 CRITICAL FIXES)

### 🔴 FIX #1: Asyncio Timeout Wrapper (2 hours)
**File:** `src/bot/broker/ibkr.py`

**What:** Override ib_insync's hardcoded 60s timeout with `asyncio.wait_for()`

**Steps:**
1. Add `import asyncio` to imports
2. Add `_fetch_historical_with_timeout()` async method before `historical_prices()` (see Action Plan line 145-185)
3. Replace `reqHistoricalData()` call with asyncio wrapper (see Action Plan line 187-220)

**Test:** 
```bash
.venv/Scripts/python.exe -m src.bot.app
# Should show historical data retrieved in 5-15s, not timing out at 60s
```

---

### 🔴 FIX #2: Exponential Backoff Retry (2 hours)
**File:** `src/bot/scheduler.py`

**What:** Add retry loop [0s, 5s, 15s] before recording failures to circuit breaker

**Steps:**
1. Add imports: `import time` and `Dict, Tuple` from typing
2. Add module-level cache: `_symbol_bar_cache: Dict[str, Tuple[Any, float]] = {}`
3. Replace historical fetch block (lines 232-264) with retry loop (see Action Plan line 273-380)

**Test:**
```bash
# Logs should show [historical_retry_sleep] and [historical_success] messages
tail -20 logs/bot.log | grep -E "historical_retry|historical_success"
```

---

### 🔴 FIX #3: Verify Market Data (1 hour)
**User Action:** Check IBKR Portal + test connection

**Steps:**
1. Log into https://www.ibkr.com/account/
2. Go to Account Settings → Market Data Subscriptions
3. Ensure "US Stocks" and "US Options" are ACTIVE
4. Test connection:
   ```bash
   .venv/Scripts/python.exe test_ibkr_connection.py --host 192.168.7.205 --port 4001 --client-id 350 --timeout 30
   ```

**Expected:**
```
✓ stock_snapshot: SPY bid=485.20 ask=485.25 last=485.23
✓ option_snapshot: SPY 15JAN26C485 bid=1.25 ask=1.30
✓ historical_1m: 60 bars retrieved
```

**If NaN:** Contact IBKR support (account permissions issue)

---

### 🟡 BONUS FIX #4: Update Defaults (10 min)
**File:** `src/bot/settings.py` lines 63-68

**Change:**
```python
# Replace "7200 S" with "3600 S"
# Replace False with True for use_rth
# Add timeout field: 90 seconds
```

See Action Plan line 415-450 for complete code.

---

## TESTING CHECKLIST

### ✅ After Fix #1 & #2:
```bash
python -m pytest tests/ -v
# Must show: 117 tests passed (0 failed)
```

### ✅ After Fix #3:
```bash
.venv/Scripts/python.exe test_ibkr_connection.py --host 192.168.7.205 --port 4001 --client-id 350
# Must show numeric prices (no NaN)
```

### ✅ Stability Test (30 min):
```bash
# Run bot for 30 minutes with 3-minute cycles
# Expected: ~10 cycles, each retrieving 30+ bars in <15 seconds
# Check logs: grep "\[HIST\] Completed" logs/bot.log
# Should NOT see "bars=0" or "Timeout"
```

### ✅ Production Ready (4 hours, next day 9:30-16:00 ET):
```bash
# Run bot during market hours
# Expected: 95%+ of cycles complete (47+ out of 48 cycles over 4 hours)
# Check: grep -i timeout logs/bot.log | wc -l
# Should return: 0 (zero timeouts)
```

---

## FILE LOCATIONS

| Fix | File | Key Lines |
|-----|------|-----------|
| #1 | `src/bot/broker/ibkr.py` | Add method ~445, modify call ~484 |
| #2 | `src/bot/scheduler.py` | Add cache ~40, replace block ~232-264 |
| #3 | IBKR Portal | Account → Market Data Subscriptions |
| #4 | `src/bot/settings.py` | Lines 63-68 |

---

## DETAILED CODE (Copy-Paste Ready)

### Fix #1 Complete Code
[See QA_AUDIT_ACTION_PLAN_20260112.md, Lines 145-220]

### Fix #2 Complete Code  
[See QA_AUDIT_ACTION_PLAN_20260112.md, Lines 273-380]

### Fix #4 Complete Code
[See QA_AUDIT_ACTION_PLAN_20260112.md, Lines 415-450]

---

## EXPECTED OUTCOME

| Before | After |
|--------|-------|
| Cycle time: 60s | Cycle time: 5-10s |
| Bars: 0 (timeout) | Bars: 30-60 ✓ |
| Circuit break after 3 tries | Retries: 3x before breaking |
| Quotes: NaN | Quotes: Valid prices ✓ |
| Production ready: NO | Production ready: YES ✓ |

---

## GIT WORKFLOW

```bash
# After completing Fix #1:
git add src/bot/broker/ibkr.py
git commit -m "Fix: Implement asyncio timeout wrapper for historical data"

# After completing Fix #2:
git add src/bot/scheduler.py
git commit -m "Fix: Add exponential backoff retry with bar caching"

# After completing Fix #4:
git add src/bot/settings.py
git commit -m "Fix: Update default historical settings to optimized values"

# Push to GitHub:
git push origin main
```

---

## TIMELINE

| Time | Task | Status |
|------|------|--------|
| Now | Fix #3: Verify subscriptions | 1 hour |
| +1h | Fix #1: Asyncio wrapper | 2 hours |
| +3h | Fix #2: Exponential backoff | 2 hours |
| +5h | Fix #4: Update defaults | 10 min |
| +5h10m | Unit tests & quick test | 1 hour |
| +6h10m | 30-min stability test | 30 min |
| **EOD** | **All critical fixes deployed** | ✓ |
| **Next day** | 4-hour RTH production test | 4 hours |

---

## HELP / DEBUGGING

### "Still getting 60s timeouts"
1. Verify Fix #1 code added correctly (asyncio import, method added, call updated)
2. Check logs for: `[historical_timeout_asyncio]` (should see if asyncio wrapper working)
3. Verify `loop.run_until_complete()` is being called, not old `reqHistoricalData()`

### "Quotes still returning NaN"
1. Check IBKR Portal → Market Data Subscriptions (must be ACTIVE)
2. Verify client ID in test matches account (310 or 350?)
3. Contact IBKR support if subscriptions show ACTIVE but still NaN

### "Tests failing after changes"
1. Revert last commit: `git revert HEAD`
2. Check exact error message
3. Fix in separate branch: `git checkout -b fix/issue-name`
4. Re-test before re-merging

---

## SUCCESS CRITERIA

When all 3 fixes are complete, bot should:
- ✅ Retrieve 30-60 bars per symbol in 5-15 seconds (not 60s timeout)
- ✅ Return valid bid/ask/last prices (not NaN)
- ✅ Retry 3 times before recording failure
- ✅ Use cached bars as fallback (if <5 min old)
- ✅ Complete 30 cycles in 30 minutes with 3-min intervals
- ✅ Show zero timeout errors in logs
- ✅ All 117 unit tests passing

---

**See QA_AUDIT_ACTION_PLAN_20260112.md for detailed code, testing, and validation procedures.**

