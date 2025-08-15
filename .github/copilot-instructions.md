# GitHub Copilot Instructions

This is an IBKR options trading bot built with Python 3.11+ featuring concurrent symbol processing, unified Pydantic configuration, and comprehensive monitoring.

## Architecture Overview

**Core Components:**
- `src/bot/broker/` - Broker abstraction with IBKR implementation
- `src/bot/strategy/` - Signal generation (scalp + whale rules)
- `src/bot/scheduler.py` - Main orchestration loop with thread-based concurrency
- `src/bot/settings.py` - Unified Pydantic v2 configuration from YAML + env
- `src/bot/execution.py` - Bracket orders and OCO emulation
- `src/bot/risk.py` - Position sizing and daily loss guards
- `src/bot/monitoring.py` - Heartbeat + Slack/Telegram alerts

**Data Flow:**
1. Scheduler fetches 1-min historical bars per symbol
2. Computes scalp signals (EMA/VWAP/RSI) + whale signals (60-min resampled)
3. Selects weekly ATM/±1 options with liquidity filters
4. Applies risk sizing and daily loss guards
5. Places orders (or logs in dry-run mode) with OCO emulation

## Key Patterns

**Broker Protocol & Stubbing:**
Use the `Broker` protocol in `src/bot/broker/base.py` for testing. See `tests/test_scheduler_stubbed.py` for the complete `StubBroker` pattern that returns deterministic data.

**Settings Management:**
```python
from src.bot.settings import get_settings
settings = get_settings("configs/settings.yaml")  # Merges YAML + env
```

**Thread Safety:**
Broker calls are serialized via `_with_broker_lock()` in scheduler. Journal writes use file-level locks. The pattern:
```python
def _with_broker_lock(fn, *args, **kwargs):
    with broker_lock:
        return fn(*args, **kwargs)
```

**Strategy Signal Format:**
All strategies return `{"signal": "BUY"|"SELL"|"HOLD", "confidence": 0.0..1.0}`. Whale signals override scalp when present.

**Structured Logging:**
Use loguru with `.bind()` for structured events:
```python
logger.bind(event="signal", symbol=symbol, action=action).info("Decision")
```

## Essential Commands

**Development:**
```bash
make venv          # Create venv + install deps
make test          # Run pytest
make fmt           # Black + ruff formatting
pre-commit install # Enable pre-commit hooks
```

**Docker:**
```bash
docker compose up --build bot                                    # Bot only
docker compose -f docker-compose.yml -f docker-compose.gateway.yml up --build  # With IBKR Gateway
```

**Key Config Files:**
- `configs/settings.yaml` - Main configuration (symbols, risk, monitoring)
- `.env` - IBKR credentials and environment variables
- Set `dry_run: true` to prevent real order placement

## Testing Conventions

**Strategy Tests:** Use synthetic pandas DataFrames with known patterns (see `tests/test_strategy.py`)
**Integration Tests:** Use `StubBroker` for deterministic scheduler cycles
**Risk Tests:** Verify position sizing and daily loss logic with controlled equity values

## Critical Implementation Notes

- **Concurrency:** Symbol processing uses `ThreadPoolExecutor` with `max_concurrent_symbols` setting
- **Option Selection:** Weekly expiry, ATM/±1 moneyness, with volume/spread filters
- **Risk Guards:** Daily loss check gates all new positions; persisted to disk for restart survival
- **OCO Emulation:** Background threads monitor fills and place TP/SL orders when native brackets unavailable
