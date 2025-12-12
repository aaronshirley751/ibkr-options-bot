# Round 3 QA Review: IBKR Options Trading Bot

**Date:** December 11, 2025  
**Scope:** Final pre-deployment audit following Round 2 fixes  
**Target:** Phase 1 deployment readiness (Raspberry Pi, paper trading)

---

## Executive Summary

After reviewing the complete codebase against Round 1 & 2 findings and project goals, I've identified **4 critical issues**, **6 high-priority items**, and **5 medium-priority enhancements** that should be addressed before deployment. The Round 2 fixes resolved major syntax errors, but residual indentation issues and a few gaps remain.

**Overall Status:** 🟡 **NEAR-READY** - Minor fixes required before deployment

---

## 🚨 CRITICAL ISSUES (Must Fix Before Deployment)

### Issue 1: Malformed Indentation in `emulate_oco()` (execution.py)

**Location:** `src/bot/execution.py` lines ~128-140

The `emulate_oco` function has corrupted indentation that will cause runtime errors:

```python
            # Safety check: exit if max duration exceeded   # <-- OVER-INDENTED
            if elapsed > max_duration_seconds:
                ...
            
                        # Progress logging every 100 iterations  # <-- OVER-INDENTED
            if iteration % 100 == 0:
```

**Copilot Prompt:**
```
Fix indentation in src/bot/execution.py emulate_oco() function. The while loop body has inconsistent indentation. All statements inside the while True loop should be at exactly 12 spaces (3 levels). Specifically fix:

1. Line ~128: "# Safety check: exit if max duration exceeded" - remove extra leading spaces
2. Line ~136: "# Progress logging every 100 iterations" - remove extra leading spaces

The correct indentation pattern inside the while loop should be:
        while True:
            iteration += 1
            elapsed = time_module.time() - start_time
            
            # Safety check: exit if max duration exceeded
            if elapsed > max_duration_seconds:
                ...

Run black formatter after fixing to ensure consistent formatting throughout the file.
```

---

### Issue 2: Missing `dry_run` Default in settings.yaml

**Location:** `configs/settings.yaml` line 8

The `dry_run` setting is `false` by default, but for Phase 1 deployment safety, it should default to `true`:

```yaml
dry_run: false  # <-- DANGEROUS for initial deployment
```

**Copilot Prompt:**
```
In configs/settings.yaml, change dry_run from false to true for safe Phase 1 deployment:

dry_run: true  # IMPORTANT: Keep true until paper trading is validated

Also add a comment explaining the setting's purpose. This prevents accidental order placement during initial deployment testing.
```

---

### Issue 3: Potential Race Condition in Daily State Persistence

**Location:** `src/bot/risk.py` `save_equity_state()` function

The atomic write pattern uses `.tmp` suffix but doesn't handle concurrent writes from multiple processes/threads:

```python
def save_equity_state(state: dict, path: Path = DEFAULT_STATE_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")  # All processes use same temp file!
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(state, f)
    tmp.replace(path)
```

**Copilot Prompt:**
```
In src/bot/risk.py save_equity_state(), add a unique suffix to the temp file to prevent race conditions when multiple processes might write simultaneously:

import os
import uuid

def save_equity_state(state: dict, path: Path = DEFAULT_STATE_PATH) -> None:
    """Save daily equity state with atomic write and unique temp file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    # Use unique temp file to prevent race conditions
    tmp = path.with_suffix(f".tmp.{os.getpid()}.{uuid.uuid4().hex[:8]}")
    try:
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(state, f)
        tmp.replace(path)
    finally:
        # Clean up temp file if replace failed
        if tmp.exists():
            tmp.unlink()
```

---

### Issue 4: Test Coverage Gap - `emulate_oco` Max Duration Guard

**Location:** `tests/test_execution.py`

The `emulate_oco` tests don't verify the `max_duration_seconds` safety guard actually exits the loop:

**Copilot Prompt:**
```
Add a test to tests/test_execution.py TestEmulateOCO class that verifies the max_duration_seconds safety guard:

def test_emulate_oco_max_duration_exit(self):
    """Emulation exits when max_duration_seconds is exceeded."""
    broker = Mock()
    contract = Mock(symbol="SPY")
    
    # Price never hits TP or SL
    broker.market_data = Mock(return_value=Mock(last=2.50))
    
    import time
    start = time.time()
    
    with patch('src.bot.execution.logger') as mock_logger:
        emulate_oco(
            broker,
            contract,
            parent_order_id="PARENT_DUR",
            take_profit=5.0,  # Never reached
            stop_loss=1.0,    # Never reached
            poll_seconds=0.01,
            side="BUY",
            quantity=1,
            max_duration_seconds=0.1,  # Very short duration for test
        )
    
    elapsed = time.time() - start
    # Should exit due to max_duration, not hang forever
    assert elapsed < 1.0  # Should exit quickly
    # Verify warning was logged
    assert any("max duration" in str(call) for call in mock_logger.warning.call_args_list)
```

---

## ⚠️ HIGH PRIORITY ISSUES (Should Fix Before Deployment)

### Issue 5: Missing Validation for Broker Connection Before Operations

**Location:** `src/bot/scheduler.py` `process_symbol()` function

The scheduler doesn't verify broker connectivity before processing symbols. A disconnected broker could cause silent failures.

**Copilot Prompt:**
```
In src/bot/scheduler.py process_symbol(), add broker connection validation at the start:

def process_symbol(symbol: str):
    try:
        # Verify broker connectivity first
        if hasattr(broker, 'is_connected') and not broker.is_connected():
            logger.warning("Broker disconnected; skipping %s", symbol)
            try:
                broker.connect()
            except Exception as e:
                logger.error("Failed to reconnect broker: %s", type(e).__name__)
                return
        
        # Check daily loss guard...
        # (rest of function)
```

---

### Issue 6: Incomplete Error Context in Exception Handling

**Location:** Multiple files use `type(e).__name__` but don't include the actual error message.

**Copilot Prompt:**
```
Update exception logging across the codebase to include error messages, not just type names. In these files:

1. src/bot/scheduler.py - Change all instances of:
   logger.exception("...failed: %s", type(e).__name__)
   to:
   logger.exception("...failed: %s: %s", type(e).__name__, str(e))

2. src/bot/broker/ibkr.py - Same pattern for all exception handlers

3. src/bot/data/options.py - Same pattern

This provides more actionable debug information in production logs.
```

---

### Issue 7: Hard-Coded Timeout Values in Broker

**Location:** `src/bot/broker/ibkr.py` multiple locations

Timeout values (2.0s, 10s) are hard-coded rather than configurable:

**Copilot Prompt:**
```
In src/bot/broker/ibkr.py, extract timeout values to class attributes that can be configured:

class IBKRBroker:
    # Configurable timeouts (seconds)
    CONNECT_TIMEOUT = 10
    MARKET_DATA_TIMEOUT = 2.0
    HISTORICAL_DATA_TIMEOUT = 30.0
    
    def __init__(self, ..., connect_timeout: Optional[int] = None, data_timeout: Optional[float] = None):
        ...
        self.connect_timeout = connect_timeout or self.CONNECT_TIMEOUT
        self.data_timeout = data_timeout or self.MARKET_DATA_TIMEOUT

Then update connect() and market_data() to use self.connect_timeout and self.data_timeout.
```

---

### Issue 8: Missing Graceful Shutdown Handler

**Location:** `src/bot/app.py`

The app handles KeyboardInterrupt but doesn't handle SIGTERM (common in Docker/systemd):

**Copilot Prompt:**
```
In src/bot/app.py, add signal handlers for graceful shutdown:

import signal
import sys

def main():
    logger.info("Starting ibkr-options-bot")
    settings = get_settings()
    
    # Setup signal handlers for graceful shutdown
    shutdown_requested = False
    
    def handle_shutdown(signum, frame):
        nonlocal shutdown_requested
        logger.info("Shutdown signal received (signal %s)", signum)
        shutdown_requested = True
    
    signal.signal(signal.SIGTERM, handle_shutdown)
    signal.signal(signal.SIGINT, handle_shutdown)
    
    # ... rest of setup ...
    
    try:
        run_scheduler(broker, settings.model_dump())
    except KeyboardInterrupt:
        logger.info("Shutting down due to KeyboardInterrupt")
    finally:
        # ... cleanup ...
```

---

### Issue 9: StubBroker Pattern Not Reusable

**Location:** `tests/test_scheduler_stubbed.py`

The `StubBroker` class is defined inline in the test file but would be useful for other tests. Extract to a shared fixture.

**Copilot Prompt:**
```
Create tests/conftest.py with shared test fixtures:

"""Shared pytest fixtures for IBKR bot tests."""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List
import pandas as pd
import pytest


@dataclass
class StubQuote:
    symbol: str
    last: float
    bid: float
    ask: float
    volume: int


@dataclass
class StubOption:
    symbol: str
    right: str
    strike: float
    expiry: str
    multiplier: int = 100


class StubBroker:
    """Deterministic broker for testing without IBKR connectivity."""
    
    def __init__(self, equity: float = 100000.0):
        self._equity = equity
        self._orders: List[Dict[str, Any]] = []
        self._connected = True
    
    def is_connected(self) -> bool:
        return self._connected
    
    def connect(self) -> None:
        self._connected = True
    
    def disconnect(self) -> None:
        self._connected = False
    
    # ... rest of StubBroker methods ...


@pytest.fixture
def stub_broker():
    """Provide a fresh StubBroker instance."""
    return StubBroker()


@pytest.fixture
def sample_settings():
    """Provide minimal valid settings for testing."""
    return {
        "symbols": ["SPY"],
        "mode": "growth",
        "dry_run": True,
        "risk": {
            "max_risk_pct_per_trade": 0.01,
            "stop_loss_pct": 0.2,
            "take_profit_pct": 0.3,
            "max_daily_loss_pct": 0.15,
        },
        "options": {"moneyness": "atm", "min_volume": 100, "max_spread_pct": 5.0},
        "schedule": {"interval_seconds": 1, "max_concurrent_symbols": 1},
        "monitoring": {"alerts_enabled": False},
    }

Then update tests/test_scheduler_stubbed.py to use the shared fixtures.
```

---

### Issue 10: No Retry Logic for Transient Broker Failures

**Location:** `src/bot/scheduler.py` broker calls in `process_symbol()`

Broker operations can fail transiently but aren't retried:

**Copilot Prompt:**
```
Add simple retry logic for transient broker failures in src/bot/scheduler.py. Create a helper:

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

def _retry_broker_call(fn, *args, max_attempts: int = 3, **kwargs):
    """Retry broker calls with exponential backoff for transient failures."""
    @retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=5),
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
        reraise=True,
    )
    def _inner():
        return fn(*args, **kwargs)
    
    try:
        return _inner()
    except Exception:
        return None

Then use _retry_broker_call() for broker.historical_prices() and broker.market_data() calls.
```

---

## 📋 MEDIUM PRIORITY (Post-Deployment Enhancements)

### Issue 11: Missing Health Check Endpoint

The bot lacks a health check for container orchestration.

**Copilot Prompt:**
```
Create src/bot/health.py with a minimal HTTP health check server:

"""Minimal health check HTTP server for container orchestration."""

import json
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Callable, Optional


class HealthHandler(BaseHTTPRequestHandler):
    check_fn: Optional[Callable[[], dict]] = None
    
    def do_GET(self):
        if self.path == "/health":
            status = self.check_fn() if self.check_fn else {"status": "ok"}
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(status).encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        pass  # Suppress logging


def start_health_server(port: int = 8080, check_fn: Optional[Callable] = None) -> threading.Thread:
    """Start health check server in background thread."""
    HealthHandler.check_fn = check_fn
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return thread
```

---

### Issue 12: Log Rotation Configuration Not Exposed

Log rotation settings are hard-coded in `logging_conf.py`.

**Copilot Prompt:**
```
In src/bot/settings.py, add LoggingSettings model and expose log rotation config:

class LoggingSettings(BaseModel):
    log_dir: str = Field(default="logs")
    max_size_mb: int = Field(default=10, ge=1, le=100)
    retention_count: int = Field(default=5, ge=1, le=20)
    json_logs: bool = Field(default=True)

Then update Settings class to include:
    logging: LoggingSettings = LoggingSettings()

Update logging_conf.py to use these settings.
```

---

### Issue 13: Position Verification in OCO Emulation (Deferred from Round 2)

The `emulate_oco` function should verify position still exists before continuing.

**Copilot Prompt:**
```
In src/bot/execution.py emulate_oco(), add position verification after the max_duration check:

# Verify position still exists (every 10 iterations to reduce broker load)
if iteration % 10 == 0:
    try:
        positions = broker.positions()
        contract_symbol = getattr(contract, 'symbol', str(contract))
        position_exists = any(
            getattr(p.get('contract', p), 'symbol', '') == contract_symbol or
            p.get('symbol', '') == contract_symbol
            for p in positions
        )
        if not position_exists:
            logger.info("Position closed externally for parent %s; exiting OCO", parent_order_id)
            break
    except Exception as e:
        logger.debug("Could not verify position: %s", type(e).__name__)
```

---

### Issue 14: Journal Path Configuration Not Validated

**Location:** `src/bot/journal.py`

The journal uses hard-coded paths that might not exist:

**Copilot Prompt:**
```
In src/bot/journal.py, add path validation and make paths configurable:

from pathlib import Path
from typing import Optional

_journal_csv: Optional[Path] = None
_journal_jsonl: Optional[Path] = None


def init_journal(csv_path: str = "logs/trades.csv", jsonl_path: str = "logs/trades.jsonl") -> None:
    """Initialize journal paths, creating directories as needed."""
    global _journal_csv, _journal_jsonl
    
    _journal_csv = Path(csv_path)
    _journal_jsonl = Path(jsonl_path)
    
    _journal_csv.parent.mkdir(parents=True, exist_ok=True)
    _journal_jsonl.parent.mkdir(parents=True, exist_ok=True)


def log_trade(trade: Dict) -> None:
    """Record trade to journal files."""
    if _journal_csv is None:
        init_journal()
    # ... rest of function using _journal_csv and _journal_jsonl
```

---

### Issue 15: Missing Type Hints in Key Functions

Several key functions lack complete type hints.

**Copilot Prompt:**
```
Add complete type hints to these functions:

1. src/bot/scheduler.py:
   - run_cycle(broker: "Broker", settings: Dict[str, Any]) -> None
   - process_symbol(symbol: str) -> None
   - _to_df(bars_iter: Any) -> Union[pd.DataFrame, List]

2. src/bot/data/options.py:
   - pick_weekly_option(...) -> Optional[OptionContract]

3. src/bot/execution.py:
   - emulate_oco(...) -> None
   - _closing_action(original_action: str) -> str

Run mypy after adding hints to verify correctness.
```

---

## Pre-Deployment Verification Checklist

After applying fixes, run this verification sequence:

```bash
# 1. Syntax validation
python -m py_compile src/bot/*.py src/bot/**/*.py

# 2. Format and lint
black src tests
ruff check --fix src tests

# 3. Type check
mypy --ignore-missing-imports src tests

# 4. Run full test suite
pytest tests/ -v --cov=src/bot --cov-report=term-missing

# 5. Verify imports
python -c "from src.bot.app import main; print('Import OK')"

# 6. Verify settings load
python -c "from src.bot.settings import get_settings; s = get_settings(); print(f'dry_run={s.dry_run}')"

# 7. Verify dry_run is True
python -c "from src.bot.settings import get_settings; assert get_settings().dry_run == True, 'dry_run must be True for deployment'"
```

**Copilot Prompt for Full Verification:**
```
Run the following verification commands and report any failures:

1. python -m py_compile src/bot/execution.py src/bot/risk.py src/bot/scheduler.py
2. black --check src tests
3. ruff check src tests  
4. pytest tests/ -v
5. python -c "from src.bot.app import main; from src.bot.settings import get_settings; s = get_settings(); print(f'Settings OK, dry_run={s.dry_run}')"
```

---

## Summary of Required Fixes

| Priority | Issue | File | Status |
|----------|-------|------|--------|
| 🚨 CRITICAL | Indentation in emulate_oco | execution.py | Must Fix |
| 🚨 CRITICAL | dry_run default | settings.yaml | Must Fix |
| 🚨 CRITICAL | Race condition in save_equity_state | risk.py | Must Fix |
| 🚨 CRITICAL | Missing max_duration test | test_execution.py | Must Fix |
| ⚠️ HIGH | Broker connection validation | scheduler.py | Should Fix |
| ⚠️ HIGH | Incomplete error messages | Multiple | Should Fix |
| ⚠️ HIGH | Hard-coded timeouts | ibkr.py | Should Fix |
| ⚠️ HIGH | Missing SIGTERM handler | app.py | Should Fix |
| ⚠️ HIGH | StubBroker not reusable | tests/ | Should Fix |
| ⚠️ HIGH | No retry logic | scheduler.py | Should Fix |
| 📋 MEDIUM | Health check endpoint | New file | Post-Deploy |
| 📋 MEDIUM | Log rotation config | settings.py | Post-Deploy |
| 📋 MEDIUM | Position verification in OCO | execution.py | Post-Deploy |
| 📋 MEDIUM | Journal path validation | journal.py | Post-Deploy |
| 📋 MEDIUM | Type hints | Multiple | Post-Deploy |

---

## Deployment Readiness Assessment

| Criteria | Status | Notes |
|----------|--------|-------|
| Syntax Valid | 🟡 | Fix emulate_oco indentation |
| Tests Passing | 🟡 | Add max_duration test |
| dry_run Safe | 🔴 | Change default to true |
| Thread Safety | 🟡 | Fix race condition in risk.py |
| Error Handling | 🟢 | Adequate for Phase 1 |
| Logging | 🟢 | Structured logging in place |
| Documentation | 🟢 | Comprehensive |
| Configuration | 🟢 | Pydantic validation |

**Recommendation:** Address all 4 CRITICAL issues and at least 3 HIGH priority issues before Phase 1 deployment. The codebase is architecturally sound and close to production-ready.

---

## Questions for Clarification

1. **Gateway Status:** Has IBKR Gateway connectivity been validated on the target Pi? This remains the primary deployment blocker mentioned in earlier reviews.

2. **Alert Configuration:** Are Slack/Telegram webhooks configured for production alerts, or should alerts remain disabled for Phase 1?

3. **Concurrent Symbols:** The default `max_concurrent_symbols: 2` - is this appropriate for Pi hardware constraints?

4. **Paper Trading Duration:** How long do you plan to run paper trading before transitioning to live? This affects whether medium-priority items should be addressed sooner.