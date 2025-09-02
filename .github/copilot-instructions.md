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
Strategy functions return standardized signals:
```python
{
    "action": "BUY" | "SELL" | "HOLD",
    "confidence": float,  # 0.0 to 1.0
    "reason": str,
    "contract": Optional[Contract]  # Selected option contract
}
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
```python
from .settings import get_settings

settings = get_settings()  # Loads YAML + env overrides
# Access nested: settings.risk.max_daily_loss_pct
# Access top-level: settings.dry_run, settings.symbols
```

### OCO Order Emulation Pattern
```python
# Prefer bracket orders, fallback to OCO emulation
try:
    # Use IBKR bracket orders when supported
    bracket_order = create_bracket_order(parent, tp_price, sl_price)
    broker.place_order(contract, bracket_order)
except Exception:
    # Fallback to background OCO monitoring
    start_oco_emulation_thread(parent_order, tp_price, sl_price)
```

## Essential Commands

### Development Workflow
```bash
# Format code (Black + isort)
make fmt

# Run linting (Ruff)
make lint

# Run type checking (MyPy)
make typecheck

# Run tests with coverage
make test

# Run all checks (CI equivalent)
make check

# Clean generated files
make clean
```

### Testing Commands
```bash
# Run specific test file
pytest tests/test_strategy.py -v

# Run integration tests with StubBroker
pytest tests/test_scheduler_stubbed.py -v

# Run with coverage report
pytest --cov=src/bot --cov-report=html

# Test specific function
pytest -k "test_scalp_signal" -v
```

### Docker Operations
```bash
# Build bot image
docker build -t ibkr-bot .

# Run with compose (bot + gateway)
docker-compose up -d

# Run bot only
docker-compose up bot

# View structured logs
docker-compose logs -f bot | jq .

# IBKR Gateway only
docker-compose -f docker-compose.gateway.yml up -d
```

## Testing Conventions

### StubBroker Pattern for Deterministic Tests
```python
from tests.test_scheduler_stubbed import StubBroker, StubQuote, StubOption

# Creates predictable market data
stub = StubBroker()
stub.add_quote("SPY", StubQuote(last=450.0, bid=449.95, ask=450.05))
stub.add_option("SPY", StubOption(conId=12345, strike=450, bid=2.50, ask=2.55))

# Simulate order fills
order_id = stub.place_order(contract, order)
stub.simulate_fill(order_id, fill_price=2.52)
```

### Test Structure and Fixtures
```python
import pytest
import pandas as pd

@pytest.fixture
def sample_bars():
    """Generate sample OHLCV data for strategy testing"""
    return pd.DataFrame({
        'open': [100, 101, 102],
        'high': [101, 103, 104], 
        'low': [99, 100, 101],
        'close': [101, 102, 103],
        'volume': [1000, 1200, 800]
    })

def test_scalp_signal_generation(sample_bars):
    # Test with known data patterns
    signal = scalp_rules.generate_signal(sample_bars)
    assert signal["action"] in ["BUY", "SELL", "HOLD"]
    assert 0.0 <= signal["confidence"] <= 1.0
```

### Risk and Safety Testing
```python
# Always test risk limits
def test_daily_loss_guard():
    # Simulate loss exceeding max_daily_loss_pct
    
def test_position_sizing():
    # Verify max_risk_pct_per_trade respected
    
def test_dry_run_mode():
    # Ensure no real orders in dry_run=True
```

## Implementation Notes

### Thread Safety and Concurrency
- **Broker Lock**: All broker operations serialized via `_with_broker_lock()`
- **Symbol Parallelism**: ThreadPoolExecutor for concurrent symbol processing
- **OCO Threads**: Background threads for take-profit/stop-loss monitoring
- **Journal Safety**: Thread-safe logging and trade recording

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

### Daily Loss Guards
```python
# Automatically persists start-of-day equity
def check_daily_loss_limit(current_equity: float) -> bool:
    start_equity = load_daily_start_equity()
    loss_pct = (start_equity - current_equity) / start_equity
    return loss_pct <= settings.risk.max_daily_loss_pct
```

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
- **StubBroker First**: Test all new features with deterministic data
- **Paper Trading**: Use IBKR paper account (port 4002) before live
- **Market Hours**: Consider trading hours and market holidays
- **Risk Limits**: Never bypass daily loss guards or position sizing
- **Secrets**: Keep `.env` files out of version control

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
