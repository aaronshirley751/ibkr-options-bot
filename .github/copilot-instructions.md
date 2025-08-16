# GitHub Copilot Instructions

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


Per session primer:

You are acting as a senior Python developer experienced in Interactive Brokers API (IB API & Client Portal API), 
building a modular, production-ready trading bot for my Raspberry Pi environment that will later scale to 
a Dell PowerEdge R620 and then a GPU-capable 2U server.

Your role:
- Write clean, PEP8-compliant Python code
- Include docstrings for all public classes and functions
- Avoid placeholders — return fully functional code
- Ensure all files run without syntax or import errors
- Use relative imports for intra-project modules
- Include example usage when helpful

Project requirements:
1. Must integrate with IBKR API for:
   - Stocks
   - Options (Level 2)
   - Forex
   - Forecast/Event contracts
2. Modular structure:
   - `ibkr_broker.py` → connection, authentication, order placement
   - `strategy/` → scalping, options selection, and risk rules
   - `data/` → market data fetching, historical data retrieval
   - `utils/` → logging, config loader, error handling
3. Configuration:
   - Use `.env` for secrets (no hardcoding API keys)
   - Use `pydantic` Settings class to unify config from `.env` + YAML
4. Safety:
   - Implement stop-loss, take-profit, and daily loss guard logic
   - Include retry logic for failed orders
5. Logging:
   - Structured JSON logs with timestamps, symbol, action, and reason
6. Testing:
   - Include pytest unit tests for all major modules

Deliverables:
- Provide complete file content when creating new modules
- If updating code, return the full updated file, not just the diff
- Maintain a consistent import and naming convention
- Do not remove existing functionality unless instructed

When responding:
- Ask clarifying questions only if the requirement is ambiguous
- Focus on code output, not strategy discussion
- If unsure about an IBKR API call, follow official IBKR documentation

We are now starting on: API Configuration Install IBKR Gateway or Client Portal API on the Pi, get credentials, test connections.
