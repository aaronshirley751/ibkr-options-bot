# QA AUDIT ACTION PLAN - Implementation Roadmap
## IBKR Options Trading Bot - Critical Fixes & Production Readiness

**Date Created:** 2026-01-12  
**Based On:** QA_AUDIT_REPORT_20260112.md  
**Total Estimated Time:** 6-8 hours (implementation) + 4 hours (validation testing)  
**Target:** Production-ready by end of day 2026-01-13

---

## EXECUTIVE SUMMARY

The QA audit identified **3 critical blockers** preventing production deployment:
1. **ib_insync timeout hardcoding** - Historical data requests fail at 60s regardless of timeout setting
2. **Market data returning NaN** - IBKR account subscriptions issue
3. **No exponential backoff retry** - Immediate failure recording causes premature circuit breaker trips

This action plan provides **step-by-step code changes** with exact file locations and complete code snippets for immediate implementation.

---

## PRIORITY 1: CRITICAL BLOCKERS (Hours 1-5)

### Fix #1: Asyncio Timeout Wrapper for Historical Data
**File:** `src/bot/broker/ibkr.py`  
**Severity:** CRITICAL - Deployment blocker  
**Est. Time:** 2 hours

**Problem:** ib_insync library ignores `RequestTimeout` setting and uses internal ~60s hardcoded timeout. Historical data requests fail after exactly 60 seconds regardless of parameter configuration.

**Solution:** Wrap `reqHistoricalData` calls with `asyncio.wait_for()` to enforce explicit timeout override.

**Step 1: Add new async method (insert around line 445, before `historical_prices()` method)**

```python
# Add these imports at top of file if not present
import asyncio

# Then add this new method before historical_prices() (around line 445):

async def _fetch_historical_with_timeout(
    self,
    contract,
    timeout: int,
    **kwargs
) -> list:
    """Fetch historical bars with explicit asyncio timeout override.
    
    This bypasses ib_insync's internal hardcoded ~60s timeout by wrapping
    the async request with asyncio.wait_for().
    
    Args:
        contract: IB contract object
        timeout: Maximum seconds to wait (overrides library default)
        **kwargs: Arguments passed to reqHistoricalDataAsync
        
    Returns:
        List of bar objects, or empty list on timeout/error
        
    Raises:
        asyncio.TimeoutError: If request exceeds timeout (caught internally)
    """
    try:
        bars = await asyncio.wait_for(
            self.ib.reqHistoricalDataAsync(contract, **kwargs),
            timeout=timeout
        )
        return bars if bars else []
    except asyncio.TimeoutError:
        logger.bind(
            symbol=contract.symbol,
            timeout=timeout,
            event="historical_timeout_asyncio"
        ).warning(
            "Historical data timeout after {}s (asyncio override attempt)",
            timeout
        )
        return []
    except Exception as e:
        logger.bind(
            symbol=contract.symbol,
            error_type=type(e).__name__,
            event="historical_error"
        ).exception("Historical data fetch error")
        return []
```

**Step 2: Modify `historical_prices()` method to use asyncio wrapper**

Find the `historical_prices()` method (around line 470) and replace the `reqHistoricalData()` call section with:

```python
# Around line 484-493, REPLACE this section:
# OLD CODE (remove):
# bars = self.ib.reqHistoricalData(
#     contract,
#     endDateTime="",
#     durationStr=duration,
#     barSizeSetting=bar_size,
#     whatToShow=what_to_show,
#     useRTH=use_rth,
#     formatDate=1,
# )

# NEW CODE (add):
# Get or create asyncio event loop for this thread
try:
    loop = asyncio.get_event_loop()
    if loop.is_closed():
        raise RuntimeError("Event loop is closed")
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

# Call async wrapper with explicit timeout override
bars = loop.run_until_complete(
    self._fetch_historical_with_timeout(
        contract,
        timeout=timeout,
        endDateTime="",
        durationStr=duration,
        barSizeSetting=bar_size,
        whatToShow=what_to_show,
        useRTH=use_rth,
        formatDate=1,
    )
)
```

**Success Criteria:**
- Historical data requests timeout after user-specified duration (e.g., 120s), not hardcoded 60s
- Logs show `[historical_timeout_asyncio]` if asyncio timeout triggers
- Test passes: 30+ bars retrieved in <15 seconds

---

### Fix #2: Exponential Backoff Retry Loop
**File:** `src/bot/scheduler.py`  
**Severity:** CRITICAL - Resource exhaustion risk  
**Est. Time:** 2 hours

**Problem:** When historical data fails, code immediately records failure to circuit breaker. During gateway hiccups, 3 transient failures halt trading unnecessarily.

**Solution:** Implement retry loop with exponential delays [0s, 5s, 15s] before recording failure.

**Step 1: Add imports and module-level cache (top of `scheduler.py`)**

Add to imports section (around line 10):
```python
import time
from typing import Dict, Tuple, Any, Optional
```

Add module-level cache after imports (around line 30-40, after existing module variables):
```python
# Symbol bar cache for fallback when fetch fails
# Structure: { symbol: (bars, timestamp) }
_symbol_bar_cache: Dict[str, Tuple[Any, float]] = {}
```

**Step 2: Replace historical data fetch block (lines 232-264)**

Find the section that starts with "# Fetch historical bars" and ends with the bars assignment and circuit breaker record_failure call. Replace the entire block with:

```python
# ============================================
# HISTORICAL DATA FETCH WITH EXPONENTIAL BACKOFF
# ============================================
retry_delays = [0, 5, 15]  # Retry at: immediately, then 5s, then 15s
bars = None
data_fetch_failed = False
last_error = None

for retry_idx, delay in enumerate(retry_delays):
    # Sleep before retry (except first attempt)
    if delay > 0:
        logger.bind(
            symbol=symbol,
            retry_number=retry_idx,
            delay_seconds=delay,
            event="historical_retry_sleep"
        ).info("Historical data retry: waiting {}s before attempt {}", delay, retry_idx + 1)
        time.sleep(delay)
    
    try:
        if not hasattr(broker, "historical_prices"):
            logger.warning("Broker does not support historical_prices method")
            break
        
        logger.bind(
            symbol=symbol,
            attempt=retry_idx + 1,
            duration=hist_duration,
            use_rth=hist_use_rth,
            timeout=hist_timeout,
            event="historical_request"
        ).debug(
            "Requesting historical data: duration={}, use_rth={}, timeout={}, attempt={}",
            hist_duration, hist_use_rth, hist_timeout, retry_idx + 1
        )
        
        # Attempt to fetch bars
        bars = _with_broker_lock(
            broker.historical_prices,
            symbol,
            duration=hist_duration,
            bar_size=hist_bar_size,
            what_to_show=hist_what,
            use_rth=hist_use_rth,
            timeout=hist_timeout,
        )
        
        # Validate that we got meaningful data
        if bars is not None and hasattr(bars, '__len__') and len(bars) > 0:
            logger.bind(
                symbol=symbol,
                bars_retrieved=len(bars),
                attempt=retry_idx + 1,
                event="historical_success"
            ).info("Historical data success on attempt {}: {} bars", retry_idx + 1, len(bars))
            
            # Cache successful data for fallback in next cycle
            _symbol_bar_cache[symbol] = (bars, time.time())
            data_fetch_failed = False
            break  # Exit retry loop - success
        else:
            # Bars is None or empty - treat as fetch failure
            bars = None
            if retry_idx == len(retry_delays) - 1:
                data_fetch_failed = True
                logger.bind(
                    symbol=symbol,
                    attempt=retry_idx + 1,
                    event="historical_empty_response"
                ).warning("Historical data returned empty response")
        
    except (TimeoutError, ConnectionError, Exception) as fetch_err:
        last_error = fetch_err
        logger.bind(
            symbol=symbol,
            attempt=retry_idx + 1,
            error_type=type(fetch_err).__name__,
            error_msg=str(fetch_err)[:100],
            event="historical_fetch_error"
        ).debug(
            "Historical data fetch error (attempt {}): {}",
            retry_idx + 1,
            type(fetch_err).__name__
        )
        
        if retry_idx == len(retry_delays) - 1:
            # All retries exhausted
            data_fetch_failed = True
            logger.bind(
                symbol=symbol,
                total_attempts=len(retry_delays),
                error_type=type(fetch_err).__name__,
                event="historical_fetch_failed_exhausted"
            ).warning(
                "Historical data fetch failed after {} attempts: {}",
                len(retry_delays),
                type(fetch_err).__name__
            )
            # Record failure to circuit breaker only after all retries
            _gateway_circuit_breaker.record_failure()

# ============================================
# FALLBACK TO CACHED BARS IF FETCH FAILED
# ============================================
if (bars is None or (hasattr(bars, '__len__') and len(bars) == 0)) and symbol in _symbol_bar_cache:
    cached_bars, cache_time = _symbol_bar_cache[symbol]
    age_seconds = time.time() - cache_time
    
    if age_seconds < 300:  # Cache valid for 5 minutes
        logger.bind(
            symbol=symbol,
            cache_age_seconds=age_seconds,
            cached_bars=len(cached_bars) if hasattr(cached_bars, '__len__') else 0,
            event="historical_cache_fallback"
        ).info(
            "Using cached bars for {} (age: {:.1f}s, bars: {})",
            symbol, age_seconds, len(cached_bars) if hasattr(cached_bars, '__len__') else 0
        )
        bars = cached_bars
    else:
        logger.bind(
            symbol=symbol,
            cache_age_seconds=age_seconds,
            event="historical_cache_stale"
        ).debug("Cached bars too old ({}s), skipping", age_seconds)
```

**Success Criteria:**
- First failed attempt retries immediately
- Second attempt waits 5s before retrying
- Third attempt waits 15s before retrying
- Circuit breaker records failure only after all retries exhausted
- Logs show `[historical_retry_sleep]`, `[historical_request]`, `[historical_success]` or `[historical_fetch_failed_exhausted]`
- Cached bars used as fallback if fetch fails but cache is <5 minutes old

---

### Fix #3: Verify Market Data Subscriptions
**Severity:** CRITICAL - Blocks signal generation  
**Est. Time:** 1 hour (user action)

**Problem:** Market data quotes returning NaN values. This blocks:
- Option premium determination (cannot size position)
- ATM strike selection (cannot pick options)
- Liquidity filtering (cannot validate spreads)

**Solution Steps:**

1. **Check IBKR Portal Subscriptions:**
   - Log into https://www.ibkr.com/account/
   - Navigate to Account Settings → Market Data Subscriptions
   - Verify status for:
     - ✓ US Stocks (Equity Level 2)
     - ✓ US Options (US Equity Options + Implied Volatility)
   - If inactive, click "Subscribe" (may be included in paper trading account)

2. **Test with Connection Checker:**
   ```bash
   cd "c:\Users\tasms\my-new-project\Trading Bot\ibkr-options-bot"
   .venv/Scripts/python.exe test_ibkr_connection.py \
     --host 192.168.7.205 \
     --port 4001 \
     --client-id 350 \
     --timeout 30
   ```

   **Expected Output (valid subscriptions):**
   ```
   {'event': 'stock_snapshot', 'symbol': 'SPY', 'last': 485.23, 'bid': 485.20, 'ask': 485.25}
   {'event': 'option_snapshot', 'symbol': 'SPY 15JAN26C485', 'bid': 1.25, 'ask': 1.30}
   ```

   **Failure Output (NaN issue):**
   ```
   {'event': 'stock_snapshot', 'symbol': 'SPY', 'last': nan, 'bid': nan, 'ask': nan}
   ```

3. **If Still NaN After Subscription Check:**
   - Contact IBKR Support: https://www.interactivebrokers.com/en/software/clientportal/clientportal.htm#support
   - Provide: Account number, API client ID, error log snippet
   - Request: "Market data quotes returning NaN via API (ib_insync)"

**Success Criteria:**
- Test output shows numeric bid/ask/last prices
- No NaN values in snapshots
- Historical bars return 30+ bars in <15s

---

### Fix #4: Update Default Configuration
**File:** `src/bot/settings.py`  
**Severity:** HIGH - Affects default behavior  
**Est. Time:** 10 minutes

**Problem:** Default settings use old configuration (2-hour extended hours) that causes timeout issues. Users without custom YAML get bad defaults.

**Step 1: Find and replace HistoricalSettings class (lines 63-68)**

```python
# BEFORE (old code):
class HistoricalSettings(BaseModel):
    duration: str = Field(default="7200 S")
    use_rth: bool = Field(default=False)
    bar_size: str = Field(default="1 min")
    what_to_show: str = Field(default="TRADES")

# AFTER (new code):
class HistoricalSettings(BaseModel):
    """Settings for historical data requests to IBKR API."""
    
    duration: str = Field(
        default="3600 S",
        description="IBKR duration string. Format: '<number> <unit>' where unit is S/D/W/M/Y. "
                    "3600 S = 1 hour of bars. Smaller durations = faster fetches."
    )
    
    use_rth: bool = Field(
        default=True,
        description="Use Regular Trading Hours only (9:30-16:00 ET). "
                    "True = faster requests, less data. False = includes pre/after hours."
    )
    
    bar_size: str = Field(
        default="1 min",
        description="Bar size: '1 min', '5 mins', '15 mins', '30 mins', '1 hour', etc."
    )
    
    what_to_show: str = Field(
        default="TRADES",
        description="Data type: 'TRADES', 'ADJUSTED_LAST', 'BID', 'ASK', 'BID_ASK', 'HISTORICAL_VOLATILITY', 'OPTION_IMPLIED_VOL'"
    )
    
    timeout: int = Field(
        default=90,
        ge=30,
        le=300,
        description="Max seconds to wait for historical data request. "
                    "IBKR library has ~60s hardcoded limit, but asyncio wrapper may extend this. "
                    "Recommended: 90-120 seconds for robustness."
    )
```

**Success Criteria:**
- Defaults match optimized values: `duration="3600 S"`, `use_rth=True`, `timeout=90`
- Type validation passes for timeout (must be 30-300)
- Documentation strings explain each field

---

## PRIORITY 2: HIGH-IMPACT FIXES (Hours 5-7)

### Fix #5: OCO Thread Health Monitoring
**File:** `src/bot/scheduler.py`  
**Severity:** HIGH - Position protection gap  
**Est. Time:** 1 hour

**Problem:** OCO emulation runs in daemon threads that die silently on exception. Positions remain open with no take-profit/stop-loss protection.

**Step 1: Add thread tracking module-level dict (around line 40-45, after other module variables)**

```python
# Active OCO emulation threads for monitoring
# Structure: { order_id: threading.Thread }
_active_oco_threads: Dict[str, threading.Thread] = {}
_active_oco_threads_lock = threading.Lock()  # Thread-safe access
```

**Step 2: Track thread when created (find emulate_oco call, around line 475-485)**

Replace this section:
```python
# BEFORE:
t = threading.Thread(
    target=emulate_oco,
    args=(broker, contract, parent_order_id, tp_price, sl_price),
    daemon=True,
)
t.start()

# AFTER:
t = threading.Thread(
    target=emulate_oco,
    args=(broker, contract, parent_order_id, tp_price, sl_price),
    daemon=True,
    name=f"OCO-{parent_order_id}",
)
with _active_oco_threads_lock:
    _active_oco_threads[parent_order_id] = t
t.start()

logger.bind(
    order_id=parent_order_id,
    symbol=symbol,
    event="oco_thread_started"
).debug("OCO emulation thread started")
```

**Step 3: Add health check in run_cycle (around line 520, after symbol processing loop)**

```python
# Add this after the main symbol processing loop completes:
def _check_oco_thread_health():
    """Monitor OCO threads for unexpected termination."""
    with _active_oco_threads_lock:
        dead_threads = []
        for order_id, thread in list(_active_oco_threads.items()):
            if not thread.is_alive():
                dead_threads.append(order_id)
                logger.bind(
                    order_id=order_id,
                    event="oco_thread_dead",
                    severity="CRITICAL"
                ).error(
                    "OCO monitoring thread died for order {}. Position may lack take-profit/stop-loss protection!",
                    order_id
                )
                # Alert user if monitoring enabled
                if settings.get("monitoring", {}).get("alerts_enabled"):
                    try:
                        alert_all(
                            settings,
                            f"🚨 CRITICAL: OCO thread died for order {order_id}. Manual intervention may be required."
                        )
                    except Exception:
                        logger.exception("Failed to send alert")
        
        # Clean up dead threads from tracking dict
        for order_id in dead_threads:
            del _active_oco_threads[order_id]

# Call health check after each cycle completes
_check_oco_thread_health()
```

**Success Criteria:**
- OCO threads tracked in `_active_oco_threads` dict
- Health check runs after each cycle
- Logs show `[oco_thread_started]` when thread created
- If thread dies: logs show `[oco_thread_dead]` with CRITICAL severity
- Alert sent if monitoring enabled

---

### Fix #6: Evaluate Stop-Loss Order Type
**File:** `src/bot/execution.py`  
**Severity:** HIGH - Slippage risk  
**Est. Time:** 30 minutes

**Problem:** Stop-Loss orders use market orders (MKT), which can fill at poor prices during volatility. 0DTE options can have 5-15% wider spreads during market stress.

**Current Code (around line 196):**
```python
ticket = OrderTicket(
    ...
    order_type="MKT",  # ⚠️ Market order - no price protection
    transmit=True,
)
```

**Recommended Change (replace order_type assignment):**

```python
# For stop-loss orders, use Stop-Limit to reduce slippage
# Add a helper function near top of execution.py:

def _calculate_sl_limit_price(
    stop_price: float,
    buffer_pct: float = 0.02,
    round_to: int = 2
) -> float:
    """Calculate limit price for stop-loss with slippage buffer.
    
    Args:
        stop_price: The stop-loss price (worst acceptable)
        buffer_pct: Buffer percentage below stop (e.g., 0.02 = 2%)
        round_to: Decimal places for limit price
        
    Returns:
        Limit price with buffer applied
    """
    limit_price = stop_price * (1.0 - buffer_pct)
    return round(limit_price, round_to)

# Then modify the order ticket creation:
# BEFORE:
# ticket = OrderTicket(
#     ...
#     order_type="MKT",
#     ...
# )

# AFTER (check if it's a SL order):
if is_stop_loss:  # You need to identify this is a SL order
    # Use Stop-Limit with 2% buffer
    limit_price = _calculate_sl_limit_price(stop_loss_price, buffer_pct=0.02)
    ticket = OrderTicket(
        ...
        order_type="STP LMT",
        aux_price=stop_loss_price,  # Stop trigger price
        limit_price=limit_price,    # Limit to no worse than this
        transmit=True,
    )
else:
    # Keep MKT for take-profit (want to exit quickly)
    ticket = OrderTicket(
        ...
        order_type="MKT",
        transmit=True,
    )
```

**Alternative (Conservative):** Keep MKT but add logging:
```python
# If changing order type is too risky, at minimum add warning logging:
logger.bind(
    symbol=symbol,
    order_type="MKT",
    risk="slippage_on_market_order",
    event="order_placement"
).warning(
    "Placing {} order at {} - consider STP LMT for SL orders to reduce slippage",
    order_type, side
)
```

**Success Criteria:**
- Stop-Loss orders use STP LMT (Stop-Limit) with 2% buffer
- Take-Profit orders continue using MKT (quick exit)
- Logs show order type for each placement
- Test order: verify limit prices are set correctly

---

### Fix #7: Add Buying Power Check
**File:** `src/bot/scheduler.py`  
**Severity:** MEDIUM - Order rejection risk  
**Est. Time:** 45 minutes

**Problem:** Position sizing uses account equity but doesn't verify options buying power. IBKR maintains separate buying power for options (usually 20-40% of NLV).

**Current Code (around line 412-419):**
```python
# Calculate position size based on risk percentage
equity = _with_broker_lock(broker.pnl).get("net", 100000.0)
size = position_size(equity, trade_risk, max_risk_pct)
# ⚠️ No check for sufficient buying power for options
```

**Step 1: Add helper function (near top of scheduler.py, around line 70-80)**

```python
def _get_available_options_buying_power(broker) -> float:
    """Get available buying power for options trading.
    
    Returns:
        Float: Available options buying power in dollars, or account equity on error
    """
    try:
        account_data = _with_broker_lock(broker.account)
        if not account_data:
            return 0.0
        
        # IBKR provides OptionBuyingPower in account summary
        opt_bp = float(account_data.get("OptionBuyingPower", 0.0))
        if opt_bp > 0:
            return opt_bp
        
        # Fallback: use net liquidation value (typically conservative)
        nlv = float(account_data.get("NetLiquidation", 0.0))
        return nlv * 0.5 if nlv > 0 else 0.0
        
    except Exception as e:
        logger.bind(
            error=type(e).__name__,
            event="buying_power_check_error"
        ).warning("Could not determine buying power: {}", type(e).__name__)
        return 0.0
```

**Step 2: Verify buying power before order placement (around line 415-425)**

```python
# BEFORE:
size = position_size(equity, trade_risk, max_risk_pct)
# Place order with size...

# AFTER:
size = position_size(equity, trade_risk, max_risk_pct)

# Verify sufficient options buying power
available_bp = _get_available_options_buying_power(broker)
required_margin = size * premium * 100  # Options are in 100-share contracts

if available_bp > 0 and required_margin > available_bp:
    # Adjust size down to fit buying power
    max_size = int(available_bp / (premium * 100))
    logger.bind(
        symbol=symbol,
        calculated_size=size,
        max_size=max_size,
        available_bp=available_bp,
        required_margin=required_margin,
        event="buying_power_limit"
    ).warning(
        "Insufficient buying power: {} contracts at ${} = ${:.2f} > ${:.2f}. Reducing to {}.",
        size, premium, required_margin, available_bp, max_size
    )
    size = max_size

if size < 1:
    logger.bind(
        symbol=symbol,
        event="insufficient_buying_power"
    ).warning("Position size 0 after buying power check - skipping trade")
    continue  # Skip this symbol
```

**Success Criteria:**
- `_get_available_options_buying_power()` returns positive value
- Position size reduced if it exceeds available buying power
- Logs show `[buying_power_limit]` when size adjusted
- Orders rejected early if size becomes 0 (instead of placing invalid orders)

---

## PRIORITY 3: CODE QUALITY (Hours 7-8)

### Fix #8: Improve Type Hints
**File:** `src/bot/scheduler.py` and others  
**Severity:** MEDIUM - Maintainability  
**Est. Time:** 1 hour

**Add proper type hints to key functions:**

```python
# At top of scheduler.py, add to imports:
from typing import Dict, List, Any, Optional, Tuple

# Function: _to_df (around line 84)
# BEFORE:
def _to_df(bars_iter) -> Any:

# AFTER:
def _to_df(bars_iter: Any) -> Optional[pd.DataFrame]:
    """Convert IBKR bar iterator to pandas DataFrame.
    
    Returns:
        DataFrame with OHLCV columns, or None if conversion fails
    """

# Function: run_cycle (around line 126)
# BEFORE:
def run_cycle(broker, settings: Dict[str, Any]):

# AFTER:
def run_cycle(broker: Broker, settings: Dict[str, Any]) -> Tuple[int, int]:
    """Execute one trading cycle.
    
    Args:
        broker: IBKR broker connection
        settings: Configuration dictionary
        
    Returns:
        Tuple of (trades_attempted, trades_executed)
    """

# Function: process_symbol (around line 180)
# BEFORE:
def process_symbol(broker, symbol: str, settings):

# AFTER:
def process_symbol(broker: Broker, symbol: str, settings: Dict[str, Any]) -> bool:
    """Process single symbol for trading signals and execution.
    
    Returns:
        True if symbol processed successfully, False on error
    """
```

**Success Criteria:**
- All public functions have parameter type hints
- Return types specified with `->` syntax
- Uses `Optional[]`, `Dict[]`, `List[]`, `Tuple[]` from typing module
- Type checker (mypy) passes with minimal errors

---

## VALIDATION & TESTING PLAN

### Phase 1: Unit Test Validation (30 minutes)

```bash
cd "c:\Users\tasms\my-new-project\Trading Bot\ibkr-options-bot"
python -m pytest tests/ -v --tb=short
```

**Expected:** All 117 tests passing (no regressions)

---

### Phase 2: Connectivity & Stability Test (1 hour)

**Step 1: Verify market data**
```bash
.venv/Scripts/python.exe test_ibkr_connection.py \
  --host 192.168.7.205 \
  --port 4001 \
  --client-id 350 \
  --timeout 30
```

**Expected Output:**
```
✓ stock_snapshot: SPY bid=485.20 ask=485.25 last=485.23
✓ option_snapshot: SPY 15JAN26C485 bid=1.25 ask=1.30
✓ historical_1m: 60 bars retrieved in 8.2s
```

**Success Criteria:**
- All snapshots return valid numeric prices (no NaN)
- Historical data returns 30+ bars
- Request time <15 seconds

**Step 2: Run 30-minute stability test**
```bash
# Create test config
cat > test_30min.yaml << 'EOF'
broker:
  read_only: true
  paper: true

schedule:
  interval_seconds: 180  # 3-minute cycles

symbols:
  - SPY

dry_run: true
EOF

# Run bot
export SETTINGS_FILE=test_30min.yaml
timeout 1800 .venv/Scripts/python.exe -m src.bot.app > logs/stability_test.log 2>&1
```

**Log Inspection:**
```bash
tail -100 logs/bot.log | grep -E "\[HIST\]|Timeout|CRITICAL"
```

**Success Criteria:**
- 10+ cycles complete (every 3 minutes = 30 minutes)
- Each cycle shows `[HIST] Completed: bars=30+` (not bars=0)
- Zero timeout errors or messages
- All quotes valid (no NaN)

---

### Phase 3: Production Readiness Test (4 hours)

**Schedule for next day during market hours (9:30-16:00 ET)**

```bash
# Create RTH config
cat > prod_readiness.yaml << 'EOF'
broker:
  read_only: true
  paper: true

schedule:
  interval_seconds: 300  # 5-minute cycles (more realistic)

symbols:
  - SPY
  - QQQ

dry_run: true

risk:
  max_daily_loss_pct: 0.15

monitoring:
  alerts_enabled: false  # Don't spam alerts during test
EOF

# Run for 4 hours during market hours
export SETTINGS_FILE=prod_readiness.yaml
nohup .venv/Scripts/python.exe -m src.bot.app > logs/prod_readiness_test.log 2>&1 &
```

**Success Criteria:**
- 95%+ cycle completion rate (47-48 cycles over 4 hours with 5min intervals)
- Average cycle time: 3-10 seconds (not 60+)
- Zero IBKR connection errors
- Valid quotes throughout day
- Daily loss guard initialized and working
- 0 timeout errors in entire log

**Log Summary:**
```bash
# Count cycle completions
grep -c "\[CYCLE\] Completed" logs/prod_readiness_test.log
# Should show 47-48

# Check for timeouts
grep -i timeout logs/prod_readiness_test.log | wc -l
# Should show 0

# Check quote validity
grep -i "nan\|not a number" logs/prod_readiness_test.log | wc -l
# Should show 0
```

---

## IMPLEMENTATION SEQUENCE

**Total Time: 6-8 hours**

| Step | Task | Time | Blocker? |
|------|------|------|----------|
| 1 | Verify IBKR subscriptions (Fix #3) | 1 hr | YES |
| 2 | Implement asyncio timeout wrapper (Fix #1) | 2 hrs | YES |
| 3 | Add exponential backoff retry (Fix #2) | 2 hrs | YES |
| 4 | Update default settings (Fix #4) | 10 min | - |
| 5 | Run unit tests | 30 min | Must pass |
| 6 | Run connectivity test | 30 min | Must pass |
| 7 | Run 30-min stability test | 30 min | Must pass |
| 8 | Add OCO thread monitoring (Fix #5) | 1 hr | - |
| 9 | Evaluate stop-loss order type (Fix #6) | 30 min | - |
| 10 | Add buying power check (Fix #7) | 45 min | - |
| 11 | Improve type hints (Fix #8) | 1 hr | - |
| 12 | Run test suite again | 30 min | Must pass |
| **13** | **Run 4-hour RTH production test** | **4 hrs** | **Validation** |

---

## CHECKPOINT CRITERIA

### Must Complete Before Proceeding to Next Phase:

**After Fix #3 (Subscriptions):**
- [ ] test_ibkr_connection.py shows valid prices (no NaN)

**After Fixes #1-2 (Async & Backoff):**
- [ ] 117 unit tests passing
- [ ] test_ibkr_connection.py passes
- [ ] 30-minute stability test passes (47+ cycles)
- [ ] Logs show exponential backoff working

**After Fixes #4-8 (Configuration & Quality):**
- [ ] 117 unit tests still passing
- [ ] Type hints validated
- [ ] New safety checks not breaking existing behavior

**Before Production:**
- [ ] 4-hour RTH production readiness test passes
- [ ] 95%+ cycle completion
- [ ] Zero timeout errors across 4+ hours
- [ ] Valid quotes throughout day
- [ ] Daily loss guard working correctly

---

## GIT COMMIT CHECKPOINTS

After each major fix, commit:

```bash
# After asyncio wrapper
git add -A
git commit -m "Implement asyncio timeout wrapper for historical data (Fix #1)"

# After backoff retry
git commit -m "Add exponential backoff retry loop (Fix #2)"

# After defaults update
git commit -m "Update historical settings defaults to optimized values (Fix #4)"

# After all critical fixes tested
git commit -m "Critical blockers resolved - ready for extended testing"
```

---

## ROLLBACK PLAN

If any fix causes regressions:

1. **Identify issue in tests or logs**
2. **Revert last commit:** `git revert HEAD`
3. **Diagnose in separate branch:** `git checkout -b fix/issue-name`
4. **Test fix locally before merging back**
5. **Re-commit with detailed fix description**

---

## SUCCESS METRICS

| Metric | Target | Current |
|--------|--------|---------|
| Unit test pass rate | 100% (117/117) | Unknown (after fixes) |
| Historical data success rate | 95%+ | TBD (after fixes) |
| Avg cycle time | 3-10s | 60s (timeout) |
| Quote validity | 100% (no NaN) | NaN (needs fix) |
| Daily uptime | 99%+ | TBD |
| Production ready | YES | In progress |

---

**Next Action:** Start with Fix #3 (verify IBKR subscriptions) to unblock market data. Then proceed through Fixes #1-4 in priority order.

