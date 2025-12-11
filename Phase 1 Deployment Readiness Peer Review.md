# QA Review: IBKR Options Trading Bot

## Executive Summary

I've conducted a comprehensive review of the codebase. The project is well-architected with clean separation of concerns, but there are several issues that should be addressed before Phase 1 deployment. The main concerns are: **low test coverage (27%)**, **thread-safety gaps**, **deprecated code patterns**, and **a legacy configuration file that conflicts with the main settings module**.

---

## Critical Issues (Must Fix Before Deployment)

### 1. Legacy Configuration File Conflict
**File:** `src/bot/config.py`

This file uses Pydantic v1 style (`BaseSettings` from `pydantic`) which is incompatible with the project's Pydantic v2 setup in `settings.py`. It's not imported anywhere but creates confusion and potential import errors.

**Copilot Prompt:**
```
Delete the file src/bot/config.py as it's a legacy configuration module that conflicts with the main settings system in src/bot/settings.py. The project uses Pydantic v2 with pydantic-settings, and this old file uses deprecated Pydantic v1 patterns. Verify no imports reference this file before deletion.
```

### 2. Broken Import in market.py
**File:** `src/bot/data/market.py` (Line 1)

Uses absolute import `from bot.broker.base import Broker` instead of relative import, which will fail when running the module.

**Copilot Prompt:**
```
In src/bot/data/market.py, fix the import statement on line 1. Change 'from bot.broker.base import Broker' to 'from ..broker.base import Broker' to use proper relative imports consistent with the rest of the codebase.
```

### 3. Thread-Safety Issues in Shared State

**Files:** `src/bot/strategy/whale_rules.py`, `src/bot/scheduler.py`

The `_debounce` dict and `_LOSS_ALERTED_DATE` dict are accessed from multiple threads without synchronization.

**Copilot Prompt:**
```
Add thread-safe access to shared module-level state in the following files:

1. In src/bot/strategy/whale_rules.py:
   - Add a threading.Lock() named _debounce_lock
   - Wrap all reads and writes to _debounce dict with the lock
   - Import Lock from threading at the top of the file

2. In src/bot/scheduler.py:
   - Add a threading.Lock() named _loss_alert_lock  
   - Wrap all reads and writes to _LOSS_ALERTED_DATE dict with the lock

This ensures thread-safe operation when processing multiple symbols concurrently via ThreadPoolExecutor.
```

### 4. Deprecated datetime.utcnow() Usage

**Files:** Multiple files use `datetime.utcnow()` which is deprecated in Python 3.12+

**Copilot Prompt:**
```
Replace all occurrences of datetime.utcnow() with datetime.now(timezone.utc) across the codebase. Files to update:
- src/bot/strategy/whale_rules.py (line 16)
- src/bot/scheduler.py (line 199)
- tests/test_strategy.py (lines 10, 32)
- tests/test_scheduler_stubbed.py (line 54)

Ensure timezone is imported from datetime module where needed. This addresses Python 3.12+ deprecation warnings.
```

---

## High Priority Issues (Should Fix Before Deployment)

### 5. Insufficient Test Coverage (27% → Target 60%+)

Critical modules lacking tests:
- `execution.py` (0% - OCO emulation is untested)
- `data/options.py` (0% - option selection logic untested)
- `monitoring.py` (0% - alerting untested)
- `broker/ibkr.py` (low coverage - bracket orders untested)

**Copilot Prompt:**
```
Create comprehensive unit tests for the following modules. Use the existing StubBroker pattern from tests/test_scheduler_stubbed.py:

1. Create tests/test_execution.py with tests for:
   - build_bracket() function with various premium/TP/SL combinations
   - is_liquid() function with liquid and illiquid quotes
   - Test edge cases: zero premium, negative percentages, missing bid/ask

2. Create tests/test_options.py with tests for:
   - nearest_friday() date calculation
   - nearest_atm_strike() with various strike ladders
   - _strike_from_moneyness() for atm, itmp1, otmp1
   - pick_weekly_option() with StubBroker returning mock chains

3. Create tests/test_monitoring.py with tests for:
   - send_heartbeat() with mock URL (use unittest.mock.patch)
   - notify_slack() with mock webhook
   - notify_telegram() with mock bot token
   - alert_all() integration

Use pytest fixtures and mock external HTTP calls. Target 80%+ coverage for these modules.
```

### 6. Bare Exception Handling

Multiple places catch `Exception` without logging or re-raising appropriately.

**Copilot Prompt:**
```
Improve exception handling across the codebase by:

1. In src/bot/broker/ibkr.py:
   - In historical_prices(), log the actual exception message before returning empty DataFrame
   - In option_chain(), add specific exception types where possible (ConnectionError, TimeoutError)

2. In src/bot/scheduler.py process_symbol():
   - Replace bare 'except Exception' in broker calls with specific exception handling
   - Always log exception details with logger.exception() not just logger.error()

3. In src/bot/data/options.py pick_weekly_option():
   - Log specific failures (which contract failed liquidity check and why)

4. In src/bot/execution.py emulate_oco():
   - Add timeout/max_iterations guard to prevent infinite loop
   - Log iteration count periodically for debugging

Follow pattern: catch specific exceptions where known, log with full context using logger.bind(), only use bare Exception for truly unexpected cases.
```

### 7. OCO Emulation Has No Exit Condition

**File:** `src/bot/execution.py`

The `emulate_oco` function runs indefinitely until TP/SL triggers. If the position is closed externally or the market never hits triggers, it loops forever.

**Copilot Prompt:**
```
In src/bot/execution.py, add safety guards to emulate_oco():

1. Add a max_duration_seconds parameter (default 8 hours / market day)
2. Add position verification - check if the position still exists before continuing
3. Add iteration counter and log every N iterations for observability
4. Add graceful exit when KeyboardInterrupt or market close is detected

The function signature should become:
def emulate_oco(
    broker,
    contract: Any,
    parent_order_id: str,
    take_profit: Optional[float],
    stop_loss: Optional[float],
    poll_seconds: int = 5,
    side: str = "BUY",
    quantity: Optional[int] = None,
    max_duration_seconds: int = 28800,  # 8 hours
):

Add position existence check by calling broker.positions() and verifying the contract is still held.
```

---

## Medium Priority Issues (Fix Soon After Deployment)

### 8. Missing Input Validation in Strategy Functions

**Copilot Prompt:**
```
Add input validation to strategy functions:

1. In src/bot/strategy/scalp_rules.py scalp_signal():
   - Validate df has required columns before accessing them
   - Add explicit check for numeric types in columns
   - Return HOLD with reason if validation fails

2. In src/bot/strategy/whale_rules.py whale_rules():
   - Validate df has 'close' and 'volume' columns
   - Validate symbol is non-empty string
   - Handle NaN values in calculations

Example validation pattern:
```python
required_cols = {'open', 'high', 'low', 'close', 'volume'}
if not required_cols.issubset(df.columns):
    return {"signal": "HOLD", "confidence": 0.0, "reason": "missing_columns"}
```
```

### 9. Hardcoded Magic Numbers

**Copilot Prompt:**
```
Extract hardcoded values in strategy files to configuration or named constants:

1. In src/bot/strategy/scalp_rules.py:
   - RSI period (14) → configurable or constant RSI_PERIOD = 14
   - EMA spans (8, 21) → constants EMA_FAST_SPAN = 8, EMA_SLOW_SPAN = 21
   - RSI thresholds (45, 70, 40) → constants RSI_OVERSOLD = 40, RSI_BUY_LOW = 45, RSI_BUY_HIGH = 70
   - Confidence weights (0.6, 0.4) → constants

2. In src/bot/strategy/whale_rules.py:
   - Debounce period (3 days) → WHALE_DEBOUNCE_DAYS = 3
   - Volume multiplier (1.5) → VOLUME_SPIKE_THRESHOLD = 1.5
   - Historical lookback (20 * 6) → LOOKBACK_BARS = 120

Add docstrings explaining why these specific values were chosen.
```

### 10. Missing Docstrings and Type Hints

**Copilot Prompt:**
```
Add comprehensive docstrings and type hints to public functions in:

1. src/bot/execution.py - all functions need Args/Returns docstrings
2. src/bot/risk.py - add type hints to all function signatures
3. src/bot/journal.py - document trade dict expected format
4. src/bot/monitoring.py - document settings dict structure expected

Follow Google-style docstrings. Example:
```python
def position_size(
    equity: float, 
    max_risk_pct: float, 
    stop_loss_pct: float, 
    option_premium: float
) -> int:
    """Calculate option contract size given equity and risk parameters.
    
    Args:
        equity: Current account equity in USD.
        max_risk_pct: Maximum percentage of equity to risk (0-1).
        stop_loss_pct: Stop loss percentage from entry (0-1).
        option_premium: Current option premium price per contract.
        
    Returns:
        Number of contracts to trade, minimum 1.
        
    Raises:
        None - returns 0 for invalid inputs.
    """
```
```

---

## Low Priority / Future Improvements

### 11. Add Integration Test with Real Market Data Shapes

**Copilot Prompt:**
```
Create tests/test_integration_dataflow.py that tests the complete data flow from raw bars to order ticket:

1. Create realistic market data fixtures (actual SPY/QQQ shaped data)
2. Test the full path: bars → _to_df → scalp_signal → pick_option → position_size → OrderTicket
3. Verify all intermediate outputs have correct types and shapes
4. Test edge cases: market gaps, pre/post market data, low volume days

Use pytest parametrize to test multiple scenarios. This validates the entire pipeline works together.
```

### 12. Add Health Check Endpoint (Future)

**Copilot Prompt:**
```
Create src/bot/health.py with a simple HTTP health check server for container orchestration:

1. Create a minimal HTTP server using http.server (stdlib)
2. Expose /health endpoint returning JSON with:
   - broker_connected: bool
   - last_cycle_time: ISO timestamp
   - daily_loss_guard_active: bool
   - symbols_processing: list
3. Make port configurable via settings
4. Run in background thread, non-blocking
5. Update Dockerfile with HEALTHCHECK instruction

This enables container orchestration (Docker, K8s) to monitor bot health.
```

---

## Test Coverage Improvement Plan

Current: 27% | Target: 60%+ for deployment

| Module | Current | Target | Priority |
|--------|---------|--------|----------|
| execution.py | 0% | 80% | HIGH |
| data/options.py | 0% | 80% | HIGH |
| monitoring.py | 0% | 70% | HIGH |
| scheduler.py | 45% | 70% | MEDIUM |
| whale_rules.py | 30% | 70% | MEDIUM |
| broker/ibkr.py | ~20% | 50% | LOW (needs Gateway) |

---

## Pre-Deployment Checklist

```
□ Delete legacy src/bot/config.py
□ Fix import in src/bot/data/market.py  
□ Add thread locks to _debounce and _LOSS_ALERTED_DATE
□ Replace datetime.utcnow() with datetime.now(timezone.utc)
□ Add tests for execution.py, options.py, monitoring.py
□ Add max_duration guard to emulate_oco()
□ Validate Gateway connectivity on Pi (make ibkr-test)
□ Run full test suite with coverage (pytest --cov)
□ Verify dry_run=true in configs/settings.yaml for initial deployment
□ Test paper trading for 1 full market day before going live
```

---

## Summary

The codebase is architecturally sound and follows good patterns. The critical blockers are:

1. **Immediate fixes needed:** Legacy config file, broken import, thread-safety issues
2. **Pre-deployment:** Test coverage needs significant improvement (27% → 60%+)
3. **Gateway blocker:** Still need to validate IBKR Gateway connectivity on Pi

Once the critical issues are addressed and test coverage improved, the project is ready for Phase 1 paper trading deployment.