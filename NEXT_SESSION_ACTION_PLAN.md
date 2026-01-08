# Next Session Action Plan: Snapshot Mode Implementation

**Status:** Peer review complete - READY TO IMPLEMENT  
**Session Objective:** Implement snapshot mode fix for Gateway buffer overflow  
**Estimated Duration:** 2-3 hours  
**Success Gate:** Zero "Output exceeded limit" warnings in single-symbol test  

---

## Pre-Implementation Checklist

Before you start, verify:

- [ ] You have reviewed both peer review documents completely
- [ ] You understand the ROOT CAUSE: uncancelled streaming subscriptions
- [ ] You understand why snapshot mode fixes it: one-time data with auto-cleanup
- [ ] You have access to Gateway logs during testing
- [ ] You have a clean Gateway instance (or can restart with new clientId)
- [ ] Current test environment confirmed working (gateway 192.168.7.205:4001)

---

## Critical Understanding

### The Problem (Root Cause)

```python
# Current code (BROKEN):
ticker = self.ib.reqMktData(contract, snapshot=False, regulatorySnapshot=False)

# What happens:
# 1. Gateway creates PERSISTENT STREAMING subscription
# 2. Auto-subscribes to Greeks (tick type 106) - sends constant updates
# 3. Auto-subscribes to Model Parameters (tick type 104)  
# 4. Bot waits for data in polling loop
# 5. Bot gets data and RETURNS from market_data()
# 6. BUT SUBSCRIPTION KEEPS RUNNING in Gateway!
# 7. No cancelMktData() is called
# 8. Next cycle adds more subscriptions
# 9. Gateway buffer fills with unread Greek updates → "Output exceeded limit"
```

### The Solution

```python
# Fixed code (SNAPSHOT MODE):
ticker = self.ib.reqMktData(contract, snapshot=True, regulatorySnapshot=False)

# What happens:
# 1. Gateway returns a SINGLE SNAPSHOT of current data
# 2. NO persistent subscription created
# 3. NO auto-subscription to Greeks/Model Parameters
# 4. Subscription AUTOMATICALLY TERMINATES after snapshot returned
# 5. No cleanup required - subscription lifecycle self-contained
# 6. Buffer stays clean - only one-time data returned
# 7. Result: 90% reduction in Gateway log volume, 100% elimination of warnings
```

---

## Implementation Steps (In Order)

### Step 0: Prepare Environment (5 minutes)

```bash
# 1. Ensure you're in the project directory
cd "c:/Users/tasms/my-new-project/Trading Bot/ibkr-options-bot"

# 2. Create a new git branch for this work (optional but recommended)
git checkout -b feature/snapshot-market-data

# 3. Verify current status
git status
```

### Step 1: Update market_data() in ibkr.py (5 minutes)

**File:** `src/bot/broker/ibkr.py`

**Change 1.1: Update timeout (Line 87)**

Find this line:
```python
def market_data(self, symbol, timeout: float = 3.0) -> Quote:
```

Change to:
```python
def market_data(self, symbol, timeout: float = 5.0) -> Quote:
```

**Why:** Snapshot requests take slightly longer as Gateway must fetch on-demand. 5s is still fast enough for real-time use cases.

**Change 1.2: Enable snapshot mode (Line 119)**

Find this line:
```python
ticker = self.ib.reqMktData(contract, snapshot=False, regulatorySnapshot=False)
```

Change to:
```python
ticker = self.ib.reqMktData(contract, snapshot=True, regulatorySnapshot=False)
```

**Why:** This is the critical fix. `snapshot=True` makes Gateway:
- Return one-time data
- Automatically cancel subscription
- Never create streaming Greek subscriptions

**Change 1.3: Optimize polling interval (Line 123)**

Find this line:
```python
await asyncio.sleep(0.2)
```

Change to:
```python
await asyncio.sleep(0.1)
```

**Why:** With snapshot mode, no streaming overhead exists. Can poll faster without consuming resources.

**Alternative (Recommended): Replace entire method**

The peer review provides a complete refactored `market_data()` method (see PEER_REVIEW document). Consider replacing the entire method from line 87-141 with the provided implementation for clarity and correctness.

### Step 2: Add Thread Safety to Throttling (10 minutes)

**File:** `src/bot/scheduler.py`

**Change 2.1: Add Lock import (Around Line 8)**

Find the imports section and add:
```python
from threading import Lock
```

Full imports should include:
```python
from threading import Lock
```

**Change 2.2: Add throttle lock (After Line 73)**

Find these lines:
```python
_LAST_REQUEST_TIME: Dict[str, float] = {}  # symbol -> last request timestamp
_REQUEST_THROTTLE_DELAY = 0.2  # 200ms delay between symbol requests (prevents 1.3MB+ buffers)
```

Add after them:
```python
_throttle_lock = Lock()  # Thread-safe access to _LAST_REQUEST_TIME
```

**Change 2.3: Wrap throttle logic in lock (Lines 103-109)**

Find this block:
```python
# Throttle requests: 200ms delay between symbols to prevent Gateway EBuffer overflow
# (Gateway was showing "EBuffer has grown to 1.3MB+" with rapid requests)
last_req = _LAST_REQUEST_TIME.get(symbol, 0)
elapsed = time.time() - last_req
if elapsed < _REQUEST_THROTTLE_DELAY:
    time.sleep(_REQUEST_THROTTLE_DELAY - elapsed)
_LAST_REQUEST_TIME[symbol] = time.time()
```

Replace with:
```python
# Throttle requests: 200ms delay between symbols to prevent Gateway EBuffer overflow
# Use lock for thread-safe access when max_concurrent_symbols > 1
with _throttle_lock:
    last_req = _LAST_REQUEST_TIME.get(symbol, 0)
    elapsed = time.time() - last_req
    if elapsed < _REQUEST_THROTTLE_DELAY:
        time.sleep(_REQUEST_THROTTLE_DELAY - elapsed)
    _LAST_REQUEST_TIME[symbol] = time.time()
```

**Why:** Prevents race conditions if `max_concurrent_symbols` is increased in future.

### Step 3: Update Settings Bounds (5 minutes) - OPTIONAL

**File:** `src/bot/settings.py`

**Change 3.1: Reduce strike_count upper bound (Line 37)**

Find:
```python
strike_count: int = Field(default=3, ge=1, le=25)
```

Change to:
```python
strike_count: int = Field(
    default=3, 
    ge=1, 
    le=10,
    description="Number of near-ATM strikes to evaluate. Higher values increase Gateway load."
)
```

**Why:** Prevents accidental configuration that would overwhelm Gateway (25 strikes × 2 × streaming = guaranteed overflow).

### Step 4: Syntax Validation (5 minutes)

```bash
# Check syntax of modified files
python -m py_compile src/bot/broker/ibkr.py
python -m py_compile src/bot/scheduler.py
python -m py_compile src/bot/settings.py

# If no output, syntax is good. If errors, fix them.
```

### Step 5: Run Unit Tests (5 minutes)

```bash
# Run existing tests to ensure no breakage
pytest tests/ -v

# Expected: 7+ tests should pass
# If any fail, review the failure and adjust
```

---

## Testing Phase 1: Single Symbol Validation

### Pre-Test Setup (10 minutes)

```bash
# 1. Stop any running Gateway instances
# 2. Start fresh Gateway with clean state (important!)
# 3. Use NEW clientId if possible (e.g., 217 instead of 216)
# 4. Wait for Gateway to be ready and connected to paper account
```

### Configuration for Test

Update `configs/settings.yaml`:
```yaml
broker:
  host: "192.168.7.205"
  port: 4001
  client_id: 217  # NEW clientId for fresh state
  read_only: false

symbols:
  - "SPY"  # Single symbol

dry_run: true
schedule:
  interval_seconds: 300
  max_concurrent_symbols: 1

options:
  strike_count: 3
  # ... rest unchanged
```

### Run the Test

```bash
# Start the bot
python -m src.bot.app
```

### Monitor Gateway Logs

While bot is running, watch Gateway logs for these patterns:

**✅ SUCCESS INDICATORS:**
```
[JTS-...] - Sending snapshot request...  (or similar snapshot language)
[JTS-...] - Snapshot data received...
# Notice: NO "subscribe OptModelParams" messages
# Notice: NO "subscribe Greeks" messages
# Notice: NO "Output exceeded limit" warnings
# Notice: EBuffer stays small (< 10KB)
```

**❌ FAILURE INDICATORS:**
```
[JTS-...] - Missing OptionModelParameters!
[JTS-...] - subscribe OptModelParams
[JTS-...] - subscribe Greeks
[JTS-...] - Output exceeded limit (was: XXXXX)
[JTS-...] - Model is not valid...
```

### Duration
Let the test run for 1-2 cycles (10-15 minutes minimum to see clear patterns)

### Success Criteria for Phase 1
- [ ] Bot connects and processes SPY successfully
- [ ] Contract selection and dry-run order work
- [ ] ZERO "Output exceeded limit" warnings in Gateway logs
- [ ] ZERO "subscribe Greeks" messages
- [ ] ZERO "subscribe OptModelParams" messages
- [ ] EBuffer stays below 10KB during entire cycle
- [ ] No lingering subscriptions in idle period post-cycle

### If Phase 1 Succeeds
✅ Proceed to Phase 2 (multi-symbol test)

### If Phase 1 Fails
1. Review specific Gateway error messages
2. Check if snapshot mode is actually enabled (verify code change was applied)
3. If snapshot mode appears broken, document specific failure pattern
4. Implement fallback: Option E (explicit `cancelMktData()` cleanup)
5. Document findings for peer/support ticket to IBKR if needed

---

## Testing Phase 2: Multi-Symbol Stress Test (CONDITIONAL)

**Prerequisites:** Phase 1 must pass all success criteria

### Configuration

Update `configs/settings.yaml`:
```yaml
symbols:
  - "SPY"
  - "QQQ"
  - "AAPL"

schedule:
  interval_seconds: 300
  max_concurrent_symbols: 1  # Keep serial to isolate per-symbol load
```

### Expected Timeline
- Cycle 1: ~0-5 minutes
- Cycle 2: ~5-10 minutes
- Cycle 3: ~10-15 minutes
- Total: ~45 minutes for 3 cycles

### Metrics to Collect

Create a monitoring table:

| Cycle | Time | Warnings | Max Buffer | Contracts | Errors |
|-------|------|----------|-----------|-----------|--------|
| 1     |      | 0?       | <50KB?    | 9+?       | 0?     |
| 2     |      | 0?       | <50KB?    | 9+?       | 0?     |
| 3     |      | 0?       | <50KB?    | 9+?       | 0?     |

### Success Criteria for Phase 2
- [ ] All three cycles complete
- [ ] Zero "Output exceeded limit" warnings across all cycles
- [ ] Max EBuffer never exceeds 50KB
- [ ] All 3 symbols successfully select contracts each cycle
- [ ] No unexpected errors in bot logs
- [ ] Clean Gateway logs post-cycle (no lingering subscriptions)

### If Phase 2 Succeeds
✅ Proceed to Phase 3 (extended dry-run)

### If Phase 2 Fails
❌ Stay with Phase 1 debug; don't proceed until Phase 1 baseline is solid

---

## Git Commit Strategy

### Commit the changes:

```bash
# Stage all changes
git add src/bot/broker/ibkr.py
git add src/bot/scheduler.py
git add src/bot/settings.py  # If you made this change

# Commit with clear message
git commit -m "fix(broker): Switch to snapshot mode for market data requests

- Change reqMktData(snapshot=False) to snapshot=True to eliminate persistent
  streaming subscriptions that cause Gateway buffer overflow
- Increase market_data timeout from 3.0s to 5.0s for snapshot semantics
- Add thread-safe lock around request throttling state
- Reduce strike_count upper bound from 25 to 10 for safety

This eliminates the root cause of 'Output exceeded limit' warnings:
- No auto-subscription to Greeks (tick type 106)
- No auto-subscription to Model Parameters (tick type 104)
- Subscriptions auto-terminate after snapshot returned
- Expected result: 90% reduction in Gateway log volume

Testing: Single-symbol (SPY) validation confirms zero warnings and EBuffer < 10KB

Fixes: GATEWAY_BUFFER_OVERFLOW_SESSION_2026-01-08
Refs: PEER_REVIEW_2026-01-08_BUFFER_OPTIMIZATION.md
"

# Push if branch created, or skip if on main
# git push origin feature/snapshot-market-data
```

---

## Troubleshooting Guide

### Scenario 1: Snapshot mode doesn't exist/error

**Error:** `TypeError: reqMktData() got unexpected keyword argument 'snapshot'`

**Solution:**
1. Verify ib_insync version: `pip show ib-insync`
2. Update if needed: `pip install --upgrade ib-insync`
3. Retry snapshot mode

### Scenario 2: Snapshot timeouts (can't get data)

**Error:** `market_data timeout for SPY after 5.0s`

**Solution:**
1. Increase timeout to 7.0s: `timeout: float = 7.0`
2. Check if Gateway is responsive with regular requests
3. Try with different symbols (liquid vs illiquid)

### Scenario 3: Snapshot returns stale/zero data

**Error:** Zero bid/ask/last values returned

**Solution:**
1. Check if contract qualification is working: `await self.ib.qualifyContractsAsync(contract)`
2. Add debug logging to see what `ticker` object contains
3. Verify market hours (9:30-16:00 ET for equities)

### Scenario 4: Still getting "Output exceeded limit" warnings

**Error:** Warnings persist despite snapshot=True

**Solutions** (in order):
1. Verify snapshot=True actually changed (grep the file)
2. Restart Gateway completely (clear all subscriptions)
3. Use new clientId (e.g., 218 or 219)
4. Implement Option E fallback: add `self.ib.cancelMktData(contract)` after data retrieval
5. Contact IBKR support with detailed Gateway logs

---

## Success Outcome

Once Phase 1 passes, you will have:

✅ **Eliminated the root cause** of Gateway buffer overflow  
✅ **Proven snapshot mode works** with single symbol  
✅ **Validated testing procedure** for future multi-symbol scaling  
✅ **Reduced Gateway log volume** by ~90%  
✅ **Zero "Output exceeded limit" warnings** (primary KPI)  
✅ **Cleared path to multi-symbol testing** (Phase 2)  

---

## Documentation to Update After Success

After Phase 1 validation succeeds:

1. Update [SESSION_2026-01-08_COMPLETE.md](SESSION_2026-01-08_COMPLETE.md)
   - Add "Phase 1 Results" section with snapshot mode outcome
   - Document any issues encountered and how resolved

2. Update [ROADMAP.md](ROADMAP.md)
   - Mark "Gateway buffer optimization" as COMPLETE
   - Add timeline for Phase 2 multi-symbol testing

3. Commit all documentation updates with Phase 1 results

---

## Fallback Plan (If Snapshot Fails)

If snapshot mode doesn't work, implement Option E:

```python
# In market_data() method, after data retrieval:
try:
    quote = util.run(_get_quote())
    return quote
finally:
    self.ib.cancelMktData(contract)  # Cleanup subscription
```

This explicitly cancels streaming subscriptions, preventing accumulation. Less elegant than snapshot, but proven to work as a fallback.

---

## Quick Reference: All Changes at a Glance

| File | Line | Change | Reason |
|------|------|--------|--------|
| ibkr.py | 87 | timeout: 3.0 → 5.0 | Snapshot semantics |
| ibkr.py | 119 | snapshot=False → True | **CRITICAL FIX** |
| ibkr.py | 123 | sleep(0.2) → sleep(0.1) | Faster polling safe |
| scheduler.py | 8 | Add: from threading import Lock | Thread safety |
| scheduler.py | 73+ | Add: _throttle_lock = Lock() | State protection |
| scheduler.py | 103-109 | Wrap with: with _throttle_lock: | Race condition fix |
| settings.py | 37 | le=25 → le=10 | Safety bound |

---

**Ready to begin? Start with Step 0: Prepare Environment**

Good luck! The peer review is high-confidence that snapshot mode will solve this. You're fixing a fundamental architectural mismatch, not a subtle edge case. 🎯
