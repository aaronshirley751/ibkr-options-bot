# AI Coding Assistant Instructions

This document provides essential guidance for AI coding agents working on the IBKR Options Trading Bot. Read this carefully to understand the architecture, patterns, and conventions that will help you be immediately productive in this codebase.

## Architecture Overview

The bot follows a clean separation of concerns with these key layers:

1. **Broker Layer** (`src/bot/broker/`):
   - Protocol-based design for testability
   - `base.py` defines the Broker Protocol with core methods
   - `ibkr.py` implements IBKR integration using ib_insync
   - Thread-safe design with connection management and serialized operations

2. **Strategy Layer** (`src/bot/strategy/`):
   - Rule-based signal generation using pandas DataFrames
   - `scalp_rules.py` for quick moves (RSI + volume indicators)
   - `whale_rules.py` for volume detection (unusual activity detection)
     - **3-day debounce per symbol**: In-memory only (resets on process restart)
     - Prevents rapid repeated signals; stores in `_debounce` dict
   - Returns structured signals with confidence scores and reasons

3. **Data Layer** (`src/bot/data/`):
   - Historical market data via broker (minute bars, 30-60 min windows)
   - Options chain filtering and selection (ATM/ITM/OTM, liquidity filters)
   - Pandas-based data processing with timezone handling

4. **Execution Layer** (`src/bot/execution.py`):
   - Bracket order management with OCO emulation
   - Background threads for take-profit/stop-loss monitoring
   - Risk-aware position sizing and paper/live trading modes

5. **Orchestration** (`src/bot/scheduler.py`):
   - Main event loop with configurable intervals (default 180s)
   - Concurrent symbol processing via ThreadPoolExecutor
   - Broker lock serialization with `_with_broker_lock()`
   - Daily loss guards and heartbeat monitoring

## Key Patterns

### Broker Abstraction with Thread Safety
```python
# Always use the Protocol for type hints
from .broker.base import Broker

def process_symbol(broker: Broker, symbol: str) -> None:
    # Broker operations are automatically serialized
    # Use _with_broker_lock() for thread safety
    pass
```

### Signal Format (Standardized)
Strategy functions return standardized dictionaries with decision signals:
```python
{
    "signal": "BUY" | "SELL" | "HOLD",  # Action (note: key is "signal" not "action")
    "confidence": float,                 # 0.0 to 1.0 confidence score
    "reason": str                        # Optional explanation (used in logging)
}
```

Example from `scalp_rules.py`:
```python
def scalp_signal(df: pd.DataFrame) -> Dict[str, Any]:
    """Compute scalp signal from 1-min bars DataFrame.
    
    df must contain columns: ['open','high','low','close','volume'] indexed by timestamp.
    Returns: {"signal": "BUY"|"SELL"|"HOLD", "confidence": 0..1}
    """
    # Indicator calculation...
    if ema_fast > ema_slow and last_price > vwap_val and 45 <= rsi_val <= 70:
        signal = "BUY"
        confidence = min(1.0, 0.6 * ema_gap_score + 0.4 * rsi_score)
    else:
        signal = "HOLD"
        confidence = 0.0
    
    return {"signal": signal, "confidence": confidence}
```

### Structured Logging with Context
```python
from .log import logger

# Bind context for structured events
logger.bind(
    symbol=symbol, 
    action="place_order",
    contract_id=contract.conId if contract else None
).info("Processing order: {}", order_type)

# Use for decision logging
logger.bind(
    cycle=cycle_count,
    symbol=symbol,
    signal=signal["action"],
    confidence=signal["confidence"]
).info("Strategy decision: {} ({})", signal["action"], signal["reason"])
```

### Configuration via Pydantic Settings
Settings are loaded from `configs/settings.yaml` with environment variable overrides via Pydantic v2. The pattern intentionally converts Settings to dict for scheduler flexibility:

```python
from .settings import get_settings

# ENTRY POINT (app.py): Load typed Settings from YAML + env
settings = get_settings()  # Returns Settings object with validation

# Access as typed object before conversion
print(settings.symbols)           # List[str]
print(settings.risk.max_daily_loss_pct)  # float with bounds

# SCHEDULER PATTERN (app.py line 26): Convert to dict for flexible access
run_scheduler(broker, settings.model_dump())  # Dict-like in scheduler

# SCHEDULER ACCESSES: Dict syntax for compatibility
trader_settings.get("symbols", [])  # In run_cycle()
trader_settings.get("risk", {}).get("max_daily_loss_pct")

# Settings model structure:
# - BrokerSettings: host, port, client_id, read_only
# - RiskSettings: max_risk_pct_per_trade, max_daily_loss_pct, take_profit_pct, stop_loss_pct
# - ScheduleSettings: interval_seconds, max_concurrent_symbols
# - OptionsSettings: expiry, moneyness (atm/itmp1/otmp1), max_spread_pct, min_volume
# - MonitoringSettings: alerts_enabled, heartbeat_url, slack/telegram

# Environment overrides use __ delimiter for nested fields:
# RISK__MAX_DAILY_LOSS_PCT=0.10  # Sets settings.risk.max_daily_loss_pct
# SYMBOLS='["SPY","QQQ"]'        # JSON for list types
```

### Order Management: Native Brackets + OCO Emulation
**IBKR.place_order()** automatically creates bracket orders with child take-profit/stop-loss orders:

```python
# When OrderTicket has take_profit_pct and/or stop_loss_pct:
# 1. Parent order transmitted first (non-blocking)
# 2. Child orders created with matching OCA group
# 3. If bracket creation fails, falls back to emulate_oco() in background thread

from .execution import emulate_oco
from threading import Thread

# OCO emulation (see execution.py lines 47-112):
oco_thread = Thread(
    target=emulate_oco,
    args=(broker, contract, parent_id, tp_price, sl_price),
    daemon=True
)
oco_thread.start()  # Polls market every 5s, places closing orders on trigger
```

## Essential Commands

### Development Workflow
```bash
# Format and lint (Black + Ruff)
make fmt

# Run all tests (7/7 tests currently)
make test

# Test with coverage report
pytest tests/ --cov=src/bot --cov-report=term-missing

# Run specific test file
pytest tests/test_strategy.py -v

# Test with StubBroker (deterministic integration tests)
pytest tests/test_scheduler_stubbed.py -v
```

### Gateway & IBKR Operations
```bash
# Start IBKR Gateway container (requires .env with IBKR_USERNAME/IBKR_PASSWORD)
make gateway-up

# View gateway logs
make gateway-logs

# Stop gateway
make gateway-down

# Test IBKR connectivity (requires gateway running)
make ibkr-test

# Test bracket order creation with what-if scenarios
make ibkr-test-whatif

# Run Python script with broker dependencies
make ibkr-deps
```

### Python Environment
```bash
# Create venv and install all dependencies
make venv

# Run bot locally (uses StubBroker by default)
python -m src.bot.app
```

## Testing Conventions

### StubBroker Pattern for Deterministic Tests
The `StubBroker` in `tests/test_scheduler_stubbed.py` provides a complete in-memory implementation for testing without IBKR connectivity. Use it for all strategy and scheduler tests:

```python
from tests.test_scheduler_stubbed import StubBroker, StubQuote

# Create broker with sensible defaults
stub = StubBroker()

# Add market data
stub.market_data("SPY")  # Returns StubQuote with default values
# Override: directly modify internal state or extend StubBroker

# Test scheduler cycle with deterministic data
from src.bot.scheduler import run_cycle
settings = {"symbols": ["SPY"], "dry_run": True, ...}
run_cycle(stub, settings)
```

### Test Structure Pattern
Tests follow a predictable structure for strategy functions:

```python
import pandas as pd
from src.bot.strategy.scalp_rules import scalp_signal

# Create sample bars using test helper
def _make_bars(n=60, base=100.0):
    """Generate OHLCV DataFrame for testing"""
    idx = pd.date_range(end=datetime.utcnow(), periods=n, freq="1min")
    close = pd.Series([base + i * 0.01 for i in range(n)], index=idx)
    return pd.DataFrame({
        'open': close,
        'high': close + 0.05,
        'low': close - 0.05,
        'close': close,
        'volume': pd.Series([1000] * n, index=idx)
    })

# Test with known conditions
def test_scalp_signal_buy_condition():
    df = _make_bars()
    sig = scalp_signal(df)
    assert sig["signal"] in ["BUY", "SELL", "HOLD"]
    assert 0.0 <= sig["confidence"] <= 1.0
```

### Key Test Files
- `tests/test_strategy.py` - Unit tests for `scalp_signal()` and `whale_rules()`
- `tests/test_scheduler_stubbed.py` - Integration tests with StubBroker
- `tests/test_config.py` - Configuration loading and validation
- `tests/test_risk.py` - Risk management functions

## Implementation Notes

### Thread Safety and Concurrency
- **Broker Lock**: All broker operations serialized via `_with_broker_lock()` in `run_cycle()`
- **Symbol Parallelism**: ThreadPoolExecutor processes symbols concurrently (default 2 workers, configurable)
- **Lock Pattern**: Broker lock is either `broker._thread_lock` (if present) or created as `Lock()` per cycle
- **Per-Symbol Safety**: Each symbol processed independently; no state sharing between threads
- **OCO Threads**: Background threads for take-profit/stop-loss monitoring (in execution layer)
- **Journal Safety**: Trade logging is thread-safe via structured logging

### Configuration Management
- **Unified Settings**: Pydantic v2 with YAML base + environment overrides
- **Nested Models**: BrokerSettings, RiskSettings, ScheduleSettings, etc.
- **Validation**: Field validators for percentages, enum values
- **Environment**: Use `__` delimiter for nested env vars (e.g., `RISK__MAX_DAILY_LOSS_PCT`)

### Logging Architecture
- **Unified Logger**: `src/bot/log.py` prefers loguru, falls back to stdlib
- **Structured Events**: JSON logging with `.bind()` for context
- **Multiple Outputs**: Text logs + JSONL for parsing
- **Log Rotation**: 10MB files, 5 file retention

### Order Management Patterns
- **Bracket Orders**: Preferred for IBKR native support
- **OCO Emulation**: Background thread monitoring for fallback
- **Paper Mode**: Always test with `paper=True` first
- **Dry Run**: Use `dry_run=True` to prevent order execution

### Daily Loss Guards with Persistence
The daily loss guard mechanism persists start-of-day equity to survive process restarts:

```python
from .risk import get_start_of_day_equity, guard_daily_loss

# Persists in logs/daily_state.json (keyed by YYYY-MM-DD)
# - Automatically initializes on first run of the day
# - Resets daily at midnight UTC/local timezone

def check_daily_loss_limit(broker, current_equity: float, max_daily_loss_pct: float) -> bool:
    start_equity = get_start_of_day_equity(broker)  # Loads from JSON persistence
    if start_equity is None:
        return False  # No guard on first run
    loss_triggered = guard_daily_loss(start_equity, current_equity, max_daily_loss_pct)
    return loss_triggered  # True = stop trading today
```

**Persistence Details**:
- File: `logs/daily_state.json`
- Format: `{"2025-12-10": 100000.0, "2025-12-11": 99500.0}`
- Timezone: Uses system/UTC timezone for date key generation
- On Restart: Loads start-of-day equity from file; continues loss tracking

## Common Tasks

### Adding a New Strategy Rule
1. Create function in `src/bot/strategy/` returning signal format
2. Process pandas DataFrame input (OHLCV bars)
3. Add comprehensive tests with various market conditions
4. Update strategy selection logic in scheduler
5. Document signal logic and confidence scoring

### Adding Configuration Settings
1. Add field to appropriate Settings model with validation
2. Update `configs/settings.yaml` with sensible default
3. Add field validator if needed (e.g., percentage bounds)
4. Update tests and document environment variable format

### Debugging Connection Issues
1. Check IBKR Gateway status: `docker-compose logs gateway`
2. Verify TWS/Gateway ports (4002=paper, 4001=live)
3. Review broker connection logs with symbol context
4. Test with `test_ibkr_connection.py` script

### Adding Monitoring/Alerts
1. Extend `MonitoringSettings` model
2. Add notification function to `monitoring.py`
3. Integrate alerts in scheduler at appropriate points
4. Test with disabled alerts first

## Important Safety Notes

- **Real Trading Bot**: Always use `dry_run: true` during development
- **StubBroker First**: Test all new features with deterministic data before IBKR integration
- **Paper Trading**: Use IBKR paper account (port 4002) before live (port 4001)
- **Market Hours**: Bot respects RTH (09:30-16:00 ET) via `is_rth()` in scheduler
- **Risk Limits**: Never bypass daily loss guards (`should_stop_trading_today()`) or position sizing
- **Secrets**: Keep `.env` files out of version control; never log sensitive data
- **Concurrency**: Always acquire `broker_lock` before broker operations in multi-threaded contexts
- **Data Availability**: Strategy expects minimum 30 bars before generating signals (see `scalp_signal()`)

## File Structure Reference
```
src/bot/
├── broker/
│   ├── base.py          # Broker Protocol definition
│   └── ibkr.py          # IBKR implementation with ib_insync
├── data/
│   ├── market.py        # Historical data and bars
│   └── options.py       # Options chain filtering
├── strategy/
│   ├── features.py      # Technical indicators
│   ├── scalp_rules.py   # Quick move detection
│   └── whale_rules.py   # Volume spike detection
├── execution.py         # Order management and OCO
├── scheduler.py         # Main orchestration loop
├── risk.py             # Daily loss guards and sizing
├── monitoring.py       # Alerts and heartbeat
├── journal.py          # Trade recording
├── settings.py         # Pydantic configuration
├── log.py             # Unified logging
└── app.py             # Entry point

tests/
├── test_strategy.py         # Strategy unit tests
├── test_risk.py            # Risk management tests
├── test_scheduler_stubbed.py # Integration with StubBroker
└── test_config.py          # Configuration tests

configs/
├── settings.yaml           # Base configuration
└── Unified configuration via Pydantic.md  # Implementation docs
```

## Quick Debugging Checklist
1. **Logs**: Check `logs/bot.log` and `logs/bot.jsonl`
2. **Config**: Verify settings load with `get_settings()`
3. **Connection**: Test broker connection independently
4. **Dry Run**: Use safe mode for testing changes
5. **StubBroker**: Isolate logic from market data issues
6. **Risk Guards**: Check daily loss limits and position sizing
7. **Symbol Processing**: Verify `_to_df()` converts bars to pandas DataFrame correctly

## Data Flow Pattern: From Bar to Order

The scheduler follows this deterministic flow:

```
1. Fetch bars via broker.historical_prices(symbol)
2. Convert to DataFrame via _to_df() 
3. Compute scalp_signal(df) on 1-min bars
4. Optionally compute whale_rules(df_60min) on 60-min resample
5. Decide final action: scalp overrides, whale backs scalp
6. Pick options contract via pick_weekly_option()
7. Get option premium via broker.market_data(contract)
8. Size position via position_size(equity, risk_pct)
9. Create OrderTicket with take_profit/stop_loss percentages
10. Place order via broker.place_order(ticket) or dry_run log
11. Record trade via log_trade()
```

Key: Each step validates output before proceeding. Missing data at any step triggers graceful skip for that symbol.

## Common Pitfalls

1. **DataFrame Checks**: Use `isinstance(obj, pd.DataFrame)` and check `len(df) >= 30` before strategy
2. **Lock Acquisition**: Always use `_with_broker_lock(fn, *args)` for broker method calls in `process_symbol()`
3. **Signal Keys**: Return dict with `"signal"` key (not `"action"`); include `"confidence"` as float 0-1
4. **RTH Filtering**: Scheduler only processes during market hours; test datetimes in `is_rth()` zone
5. **Settings Access**: Use `settings.get("key")` for dict-like access in scheduler; use dot notation for `Settings` objects
6. **Resample Syntax**: Use `df.resample("60T")` for 60-minute bars with proper time-aware index

---

## Legacy Session Context (Historical Reference)

The following section maintains context for AI session consistency during development phases:

**Primary Development Focus:**
You are acting as a senior Python developer experienced in Interactive Brokers API (IB API & Client Portal API), building a modular, production-ready trading bot for Raspberry Pi environment that will later scale to Dell PowerEdge R620 and GPU-capable 2U server.

**Core Requirements:**
- Clean, PEP8-compliant Python with comprehensive docstrings
- Full IBKR API integration (stocks, options Level 2, forex, forecast contracts)
- Modular structure with broker abstraction, strategy isolation, and data management
- Pydantic Settings for unified configuration (`.env` + YAML)
- Comprehensive safety: stop-loss, take-profit, daily loss guards, retry logic
- Structured JSON logging with timestamped events
- Complete pytest coverage for all major modules

**Implementation Standards:**
- Avoid placeholders; return fully functional code
- Use relative imports for intra-project modules
- Include example usage when helpful
- Return complete file content for new modules/updates
- Maintain consistent import and naming conventions
- Follow official IBKR documentation for API usage
