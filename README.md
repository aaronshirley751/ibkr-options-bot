# ibkr-options-bot

Lightweight scaffold for an IBKR options trading bot.

Structure and goals are in the repository root. This project is a starting point and intentionally minimal — add credentials to `.env` and tune `configs/settings.yaml` before running.

## 🚀 Start Here for Next Session

### Current Status Summary
- ✅ **Local Development Environment**: Python 3.12.10 installed, all dependencies ready, 7/7 tests passing
- ✅ **Code Quality**: Comprehensive test suite with 27% coverage, linting tools configured
- ✅ **AI Guidance**: Updated `.github/copilot-instructions.md` with comprehensive patterns and conventions
- ⏳ **Pi Gateway**: Alternative Docker configurations prepared, authentication scripts ready
- ⏳ **End-to-End Testing**: Awaiting Gateway resolution for connectivity validation

### Immediate Priorities

#### PRIORITY 1: Pi Gateway Resolution
**Current Blocker**: Docker image access for IBKR Gateway deployment
**Ready Solutions**:
- `scripts/test_gateway_options.sh` - Test all Docker alternatives automatically
- `docker-compose.gateway-vnexus.yml` - VNC-based Gateway with authentication
- `docker-compose.gateway-uaf.yml` - UAF Gateway alternative
- `docs/GATEWAY_AUTH_INSTRUCTIONS.md` - Step-by-step authentication guide

**Next Actions**:
1. Run `bash scripts/test_gateway_options.sh` on Pi to test all alternatives
2. If successful: `make ibkr-test` for connectivity validation
3. If blocked: Follow manual Gateway installation from `docs/IBKR_SETUP.md`

#### PRIORITY 2: Local Development Ready
**Current Status**: ✅ Fully functional
**Testing Commands**:
```bash
# Run all tests (7/7 passing)
pytest tests/ -v

# Run with coverage (27% current)
pytest tests/ --cov=src/bot --cov-report=term-missing

# Code quality
ruff check src tests && black src tests
```

#### PRIORITY 3: Production Readiness
**Next Development Steps**:
- Increase test coverage (current: 27%, target: 60%+)
- Add broker protocol integration tests
- Implement end-to-end paper trading validation
- Performance testing with concurrent symbols

### Quick Commands

#### Local Testing
```bash
# Development environment ready
pytest tests/ -v                    # All tests (7/7 passing)
python -m src.bot.app               # Run bot locally (stub broker)
make test                          # Full test suite
```

#### Pi Deployment
```bash
# On Pi - test Gateway options
bash scripts/test_gateway_options.sh

# If Gateway working
make ibkr-test                     # Test IBKR connectivity
make run                          # Production deployment
```

#### Development Workflow
```bash
# Code quality (already configured)
ruff check --fix src tests        # Auto-fix linting
black src tests                   # Format code
mypy src tests                    # Type checking
```

### Architecture Overview

This bot implements a **protocol-based broker architecture** with:
- **Broker Abstraction**: Protocol interface allowing StubBroker (testing) and IBKRBroker (production)
- **Strategy Layer**: Scalp rules and whale detection with configurable parameters
- **Risk Management**: Position sizing, daily loss guards, thread-safe operations
- **Orchestration**: Scheduler with cron-like execution, structured logging

**Key Files**:
- `src/bot/app.py` - Main application entry point
- `src/bot/broker/ibkr.py` - IBKR connectivity and order management
- `src/bot/strategy/scalp_rules.py` - Primary trading strategy
- `configs/settings.yaml` - Configuration management
- `.github/copilot-instructions.md` - AI agent guidance (200+ lines)

## Development Setup

### Quickstart
1. **Python Environment** (✅ Complete):
   ```bash
   # Virtual environment ready with Python 3.12.10
   # All dependencies installed (core + development)
   ```

2. **Configuration**:
   ```bash
   cp .env.example .env              # Add IBKR credentials
   vim configs/settings.yaml        # Tune strategy parameters
   ```

3. **Testing** (✅ Validated):
   ```bash
   pytest tests/ -v                 # 7/7 tests passing
   ```

4. **Gateway Deployment**:
   ```bash
   # On Pi - test options
   bash scripts/test_gateway_options.sh
   ```

### Documentation
- `ROADMAP.md` - Phased deployment strategy
- `docs/TESTING_OUTCOMES.md` - Comprehensive test results and coverage analysis
- `docs/IBKR_SETUP.md` - IBKR account and Gateway setup
- `docs/GATEWAY_AUTH_INSTRUCTIONS.md` - Docker authentication solutions

Pre-commit hooks
-----------------

Install tooling and enable hooks locally so formatting, linting, and typing run before each commit:

```bash
python -m pip install -r requirements-dev.txt
pre-commit install
```

You can run the hooks against all files on demand:

```bash
pre-commit run --all-files
```

Raspberry Pi notes
------------------

- This project targets Python 3.11+. On Raspberry Pi (aarch64) install system build deps before pip where needed:
	- Debian/Ubuntu: `sudo apt-get install build-essential libatlas-base-dev libopenblas-dev gfortran python3-dev`
	- Installing `numpy`/`pandas` may require additional time; prefer wheels if available for your platform.

IB Gateway / TWS
----------------

- Install and run IB Gateway or TWS locally on a machine reachable from this bot.
- Configure API settings in IB Gateway: enable API, set Socket Port (paper default 4002), set trusted IPs if needed.

Environment variables
---------------------

- `TZ` – timezone to use; default example: `America/New_York`
- `IBKR_HOST` – host where IB Gateway/TWS is running (default 127.0.0.1)
- `IBKR_PORT` – port (paper default 4002)
- `IBKR_CLIENT_ID` – int client id for IB API

Monitoring & alerts
-------------------

- Heartbeat: set `monitoring.heartbeat_url` (e.g., Healthchecks.io) to ping at the start of each active cycle.
- Alerts: enable `monitoring.alerts_enabled` and optionally set `slack_webhook_url` and/or Telegram `telegram_bot_token` + `telegram_chat_id`.
- The bot sends an alert once per day when the daily loss guard triggers, and on unexpected run_cycle errors.

Market data requirements
------------------------

- The bot assumes market data access is available via IB Gateway/TWS.
- For scalp rules the scheduler expects 1-minute OHLCV bars covering the last ~60 minutes.
- For whale rules it expects at least 60-minute bars covering a longer window (20 days x ~6 bars/day).

Safety & risk disclaimer
------------------------

- This project is a development scaffold and not financial advice. Trading options involves substantial risk.
- Test extensively in paper-mode with small sizes before going live.
- Use the `max_daily_loss_pct` and `max_risk_pct_per_trade` settings to limit exposures.
 - Set `dry_run: true` in `configs/settings.yaml` to prevent real order placement while testing; the bot will log intended actions only.

Security hardening
------------------

- Ensure `.env` file is present but not committed (repo `.gitignore` covers it). On Unix systems, restrict permissions: `chmod 600 .env`.
- Avoid logging secrets. The bot does not print environment variables and only logs high-level events.
- Keep logs in `logs/` (ignored by git). Rotate is configured via loguru.


Start Here
----------

1) Create and activate a virtual environment, then install deps:

```bash
make venv
```

2) Configure settings and env:

- Edit `configs/settings.yaml` (broker host/port/client_id, symbols, risk, options, journal).
- Copy `.env.example` to `.env` and adjust values.

3) Run the bot (paper/test environment recommended first):

```bash
./scripts/run_bot.sh
```

4) Run tests and format:

```bash
make test
make fmt
```

5) Install user-level systemd service (Linux):

```bash
./scripts/install_systemd.sh
systemctl --user status ibkr-bot.service
```


Current status (summary)
------------------------

- Core scaffold is in place: broker protocol, IBKR implementation (skeleton), strategies (scalp + whale), risk sizing, scheduler, execution helpers, journaling, scripts.
- Scheduler loop runs during RTH (ET) and calls `run_cycle` per interval.
- Strategies use pandas; whale signal has a 3‑day debounce per symbol (in-memory).
- Execution supports bracket construction and an emulated OCO watcher thread.
- README includes Raspberry Pi notes, IB Gateway setup, env vars, and disclaimers.


Progress update (2025-08-15)
----------------------------

What’s done
- Added optional IBKR deps file `requirements-ibkr.txt` and Make targets: `ibkr-deps`, `ibkr-test`, `ibkr-test-whatif`, and gateway helpers `gateway-up/down/logs`.
- Implemented `test_ibkr_connection.py` to validate Gateway connectivity (stock/forex/options snapshots, historical bars, optional what-if bracket).
- Created `docs/IBKR_SETUP.md` with Raspberry Pi SSH workflow and Docker Compose overlay usage.
- Fixed and simplified `docker-compose.gateway.yml` to be a standalone Gateway overlay.
- Structured logging, tests, CI, Dockerfile, and roadmap are in place from earlier milestones.

Lessons learned
- Raspberry Pi had legacy apt sources (mopidy) causing `apt-get update` failures—removed stale entries before installing packages.
- GHCR image `ghcr.io/gyrasol/ibkr-gateway:latest` requires authentication; pulling anonymously on the Pi returned `denied`.
- The Pi environment reported Python 3.7 by default; the project targets Python 3.11+. A newer OS image (Bullseye/Bookworm 64-bit) or Python 3.11 via pyenv is advised for parity and long-term support.

Blockers / decisions
- Gateway container image: choose between
	1) Authenticate to GHCR (create a GitHub PAT with read:packages and `docker login ghcr.io` on the Pi), or
	2) Switch to a public IB Gateway image (no auth), updating `docker-compose.gateway.yml` accordingly.
- Pi Python version: optional for the connectivity test (works with ib_insync on 3.7), but upgrade to Python 3.11+ is recommended for the bot runtime.

Start here: Next steps (Gateway + connectivity)
-----------------------------------------------

1) Decide Gateway image path
- Preferred (secure): authenticate and keep `ghcr.io/gyrasol/ibkr-gateway:latest`.
	- On the Pi: `docker login ghcr.io -u <github-username>` (password = GitHub PAT with read:packages)
- Alternate: switch to a public image in `docker-compose.gateway.yml` and run without login.

2) Ensure `.env` has credentials for paper Gateway
- `IBKR_USERNAME=...` and `IBKR_PASSWORD=...`
- `TZ=America/New_York` (or your timezone)

3) Bring up Gateway on the Pi
```bash
make gateway-up
docker ps --filter name=ibkr-gateway --format '{{.Names}} | {{.Status}}'
```

4) Run connectivity test (on the Pi)
```bash
make venv
make ibkr-deps
make ibkr-test
# Optional safe what-if bracket order
make ibkr-test-whatif
```

5) When done
```bash
make gateway-down
```

Operational tip: keep `dry_run: true` in `configs/settings.yaml` until you fully validate data, sizing, and bracket behavior.


Known gaps and items to strengthen
----------------------------------

1) Configuration unification
	- Adopt a single typed settings module (pydantic‑settings) that merges YAML + `.env` with schema validation.

2) Broker data APIs
	- Implement `historical_prices(symbol, duration, barSize)` on `IBKRBroker` via `reqHistoricalData` (1‑min and 60‑min OHLCV).
	- Make `market_data` accept either a stock symbol or an option contract, returning the correct quote.
	- Clarify `OptionContract` fields (e.g., include `localSymbol`) and ensure option quotes use the option contract, not the underlying.

3) Scheduler resiliency
	- Ensure `_to_df` always returns a DataFrame; guard against unbound variables.
	- Add weekend/us‑holiday skips (placeholder TODO exists) and better error metrics.

4) Execution robustness
	- `build_bracket` type should accept/return Optional floats; wire actual close orders inside `emulate_oco`.
	- Improve `is_liquid` for options (use volume/open interest if available; consider spread in absolute cents too).

5) Tests and mocks
	- Add unit tests for strategies (scalp/whale) with synthetic DataFrames.
	- Create a `FakeBroker` to unit‑test `run_cycle` without IB.
	- Keep IB‑dependent code out of unit tests.

6) CI/CD
	- Add GitHub Actions: ruff, black --check, mypy, pytest.
	- Add pre‑commit hooks to enforce formatting/linting locally.

7) Monitoring
	- Add retries/backoff for webhooks, redact secrets in logs, and consider Sentry for exception tracking.


Prioritized next steps (suggested)
----------------------------------

1) Implement `IBKRBroker.historical_prices` (1m/60m) and option quoting.
2) Introduce a typed settings model (pydantic‑settings) and update `app.py` usage.
3) Fix small type/lint issues (scheduler `_to_df`, `build_bracket` return types, remove unused helpers).
4) Add `FakeBroker` and tests for `run_cycle`, strategies, and execution helpers.
5) Add CI workflow and pre‑commit.


Git: local commit and pushing to GitHub
--------------------------------------

If you haven’t initialized a git repo yet:

```bash
git init
git add -A
git commit -m "feat: initial ibkr-options-bot scaffold"
```

Then add a remote and push (replace owner/repo):

```bash
git remote add origin git@github.com:<owner>/<repo>.git
git branch -M main
git push -u origin main
```

If you prefer HTTPS:

```bash
git remote add origin https://github.com/<owner>/<repo>.git
git push -u origin main
```

Docker usage
------------

Build the image and run the bot (expects `.env` and `configs/settings.yaml` locally):

```bash
docker build -t ibkr-options-bot:latest .
docker run --rm \
	--env-file .env \
	-e TZ=${TZ:-America/New_York} \
	-v "$PWD/configs:/app/configs:ro" \
	-v "$PWD/logs:/app/logs" \
	ibkr-options-bot:latest
```

Compose: bot only

```bash
docker compose up --build bot
```

Compose overlay with IBKR Gateway (paper)

```bash
# Ensure IBKR_USERNAME/IBKR_PASSWORD exist in .env
docker compose -f docker-compose.yml -f docker-compose.gateway.yml up --build
```

Parallelism & scalability
-------------------------

- The scheduler can process multiple symbols concurrently using threads. Control via `schedule.max_concurrent_symbols` (default 2).
- Broker calls are serialized through an internal lock to avoid thread-safety issues in client libraries; adjust if your broker impl is thread-safe.
- Journal writes are protected with a file lock to avoid corruption.


Progress update (2025-08-16)
----------------------------

What’s done
- Introduced a unified logger shim at `src/bot/log.py` that prefers loguru and falls back to stdlib logging.
- Made `src/bot/logging_conf.py` resilient: uses the unified logger and no-ops when loguru sinks aren’t available.
- Hardened `src/bot/scheduler.py` against missing pandas: added guards to only use DataFrame operations when available.
- Cleaned indentation and stabilized formatting issues that previously tripped static checks.

Pi Setup Progress (2025-08-16 afternoon)
- SSH connection established to Pi (192.168.7.117)
- Repository updated to latest version with all recent changes
- Python 3.7.3 confirmed available (older than target 3.11+ but sufficient for ib_insync)
- Virtual environment exists and has key packages: ib-insync 0.9.86, pandas 1.3.5
- Environment file (.env) configured with IBKR paper credentials
- Docker 24.0.1 available and ready

Gateway Image Challenges
- Original GHCR image (ghcr.io/gyrasol/ibkr-gateway:latest) requires authentication - access denied
- Attempted multiple public alternatives:
  - voyz/ib-gateway:paper - repository does not exist
  - rylorin/ib-gateway:latest - access denied
  - ibcontroller/ib-gateway:latest - access denied
- All public IB Gateway images tested returned "pull access denied" or "repository does not exist"
- Current blocker: Need to find a working public IB Gateway image or set up GHCR authentication

Connectivity Test Results
- test_ibkr_connection.py runs successfully but fails at connection step (expected - no Gateway running)
- Error: ConnectionRefusedError on port 4002 (confirms no Gateway is listening)
- All prerequisites for connectivity testing are in place once Gateway is resolved

Notes
- Local Windows shell currently lacks Python (venv creation failed). Tests will pass once Python 3.11+ is installed.
- Pi environment is fully prepared for IBKR testing - only Gateway deployment remains as blocker.

**Gateway Resolution Options (2025-08-16)**
1. **GHCR Authentication** (Recommended for security):
   ```bash
   # Create GitHub Personal Access Token with read:packages scope
   # On Pi: docker login ghcr.io -u <github-username>
   # Password: use the PAT token
   # Then: make gateway-up
   ```

2. **Public Image Search**: Continue searching for working public IB Gateway alternatives

3. **Manual Gateway Installation**: Download IB Gateway directly from IBKR and run without Docker

Start here: bite-size next steps
1) **Gateway Resolution (Critical)**: Choose one of these paths:
   - Create GitHub Personal Access Token with read:packages scope and authenticate: `docker login ghcr.io -u <username>`
   - Find a working public IB Gateway image or build one from IBKR's official installer
   - Set up IB Gateway manually without Docker (download and install directly)
2) **Once Gateway is running**: Execute `make ibkr-test` on Pi for end-to-end validation
3) **Local dev**: Install Python 3.11+, set up venv, and run tests locally
4) **CI**: Add GitHub Actions workflow once local testing is validated
