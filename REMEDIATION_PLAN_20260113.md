# Remediation Plan: IBKR Options Bot Restoration
**Date:** January 13, 2026
**Target:** Restore functionality and align with project goals.

## 1. Problem Statement
The bot is currently misaligned with project goals due to a critical failure in the **Data Layer**. Specifically, the `historical_prices` method in `src/bot/broker/ibkr.py` consistently fails to retrieve data (timeout at 60s, 0 bars returned), masking all downstream functionality types (strategy, execution).

A diagnostic test (`diagnostic_test.py`) has proven that the IBKR Gateway and network are functional. The issue is isolated to the bot's implementation of the data request wrapper.

## 2. Root Cause Analysis
The discrepancy between the failing bot and the working diagnostic test reveals the root cause:
- **Diagnostic Test (Working):** Uses `ib_insync`'s native synchronous `reqHistoricalData()` method. This relies on the library's internal handling of the event loop.
- **Bot Implementation (Failing):** Wraps the request in a complex manual `asyncio` loop with `loop.run_until_complete` and `asyncio.wait_for`.
- **Conclusion:** The manual async wrapper is conflicting with `ib_insync`'s internal state management or signal handling, causing the `RequestTimeout` to be ignored and the request to hang/timeout at the default TCP/socket level (60s) instead of the application level.

## 3. Remediation Strategy
**Simplify execution.** We will refactor the Broker layer to use the usage pattern proven by the diagnostic test. We will remove the custom `asyncio` loop management within `historical_prices` and rely on `ib_insync`'s native synchronous interface, which is designed to be thread-safe and robust when running in a `ThreadPoolExecutor` (which the scheduler uses).

---

## 4. Implementation Steps

### Phase 1: Refactor `historical_prices` (Immediate Priority)
**Goal:** Replace the faulty async wrapper with a direct library call.

**Action:**
Modify `src/bot/broker/ibkr.py`.
1.  **Remove** the `_fetch_historical_with_timeout` internal async wrapper.
2.  **Remove** `loop.run_until_complete` and `asyncio.wait_for` logic.
3.  **Implement** a direct call to `self.ib.reqHistoricalData(...)`.
4.  **Retain** the `RequestTimeout` setting (checking if the library respects it globally or per-request).

**Code Pattern to Adopt (Proven):**
```python
# From diagnostic_test.py logic
bars = self.ib.reqHistoricalData(
    contract,
    endDateTime='',
    durationStr=duration,
    barSizeSetting=bar_size,
    whatToShow='TRADES',
    useRTH=use_rth,
    formatDate=1,
    keepUpToDate=False,
    chartOptions=[]
)
```

### Phase 2: Fix Fallback Mechanism
**Goal:** Ensure resilience if the primary request fails.

**Action:**
1.  Simplify the fallback logic. If `bars` is None or empty after the primary call, retry *once* with a slight delay and potentially simplified parameters (e.g., smaller duration).
2.  Add explicit logging **before** the fallback triggers: `logger.warning(f"Primary request returned 0 bars for {symbol}. Attempting retry...")`.
3.  Ensure exceptions in the primary call are caught specifically (e.g., `asyncio.TimeoutError` or `WrapperError`) and trigger the fallback path.

### Phase 3: Validation and Verification
**Goal:** Confirm the bot matches `diagnostic_test.py` performance.

1.  **Verify Data Flow:**
    - Run bot.
    - Confirm logs show: `[HIST] Completed: symbol=SPY, elapsed=1.XXs, bars=61`.
2.  **Verify Timeout Config (Optional):**
    - Once working, test with `timeout=1` to ensure it actually times out (validating control).

---

## 5. Execution Plan

1.  **Git Branch:** Create new branch `fix/data-retrieval-simplification`.
2.  **Edit:** `src/bot/broker/ibkr.py`.
3.  **Test:** Run `python -m src.bot.app`.
4.  **Commit:** If successful, commit changes.
5.  **Documentation:** Update engineering log with findings.

## 6. Alignment Check
This plan aligns with the project goal "Production-Ready Trading Bot" by:
- removing "clever" but fragile code.
- relying on the vendor library's standard, tested paths `ib_insync`.
- prioritizing stability (getting data) over theoretical optimizations (manual async management).
