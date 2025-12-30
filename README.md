# ibkr-options-bot

Lightweight scaffold for an IBKR options trading bot.

Structure and goals are in the repository root. This project is a starting point and intentionally minimal — add credentials to `.env` and tune `configs/settings.yaml` before running.

---

## 🚀 **START HERE NEXT SESSION (Session 12/30/2025 → 12/31/2025)**

### **Sessions 12/29-12/30 Summary: Infrastructure Ready + Architecture Discovery**

**Combined Progress**: ✅ 8 of 16 steps complete (50%)  
**Code Status**: ✅ 116/116 tests passing - READY FOR QA REVIEW  
**Deployment Status**: ⚠️ Gateway architecture blocker discovered - SOLUTION IDENTIFIED  

See [docs/QA_READINESS_CHECKLIST.md](docs/QA_READINESS_CHECKLIST.md) for comprehensive QA assessment and [SESSION_12_30_2025_SUMMARY.md](SESSION_12_30_2025_SUMMARY.md) for detailed investigation findings.

---

### **✅ COMPLETED STEPS (1-8 of 16)**

1. ✅ **OS Flashed**: 64-bit Raspberry Pi OS (Debian Trixie)
2. ✅ **Pi Booted**: Accessible at 192.168.7.117, hostname "Jeremiah"
3. ✅ **SSH Configured**: saladbar751@Jeremiah working
4. ✅ **Python Installed**: Python 3.11.9 via pyenv
5. ✅ **Repository Cloned**: Bot source at `~/ibkr-options-bot`
6. ✅ **Dependencies Installed**: All packages in venv (pandas-ta removed as unused)
7. ✅ **Environment Configured**: `.env` with IBKR credentials (chmod 600)
8. ✅ **Docker Installed**: Engine 29.1.3 + Compose v2.27.1

### **✅ CODE QUALITY VALIDATED (Step 17)**

```
pytest results: 116/116 PASSING (100%)
  ✅ test_config.py .................. 7 passed
  ✅ test_execution.py .............. 20 passed  
  ✅ test_integration_dataflow.py ... 5 passed
  ✅ test_monitoring.py ............ 43 passed
  ✅ test_options.py ............... 23 passed
  ✅ test_risk.py ................... 2 passed
  ✅ test_scheduler_stubbed.py ...... 1 passed
  ✅ test_strategy.py ............... 3 passed
  Execution time: 14.01s (all modules tested)
```

---

### **⚠️ ARCHITECTURE BLOCKER: IBKR Gateway on Raspberry Pi**

**ROOT CAUSE DISCOVERED**: IBKR Gateway is **x86_64-only software**

```
Raspberry Pi 4: ARM64 (aarch64) processor
IBKR Gateway:   x86_64 (Intel/AMD) ONLY
Result:         Cannot run natively on Pi
```

**Investigation Completed** (Session 12/30):
- ✅ Tested 3 alternative Docker images: All unavailable or x86-only
- ✅ Attempted manual installation: Downloaded 304MB x86_64 binary
- ✅ Diagnosed failure: "Exec format error" → x86_64 binaries incompatible with arm64
- ✅ Searched Docker Hub: No arm64v8 official variants found
- ✅ Verified IBKR distributions: Windows/Mac/Linux x86_64 only

---

### **🎯 SOLUTION: Remote x86 Gateway (RECOMMENDED)**

**Architecture Change Required**:
```
┌──────────────┐  Network   ┌─────────────────┐
│ Raspberry Pi │────TCP──→  │ x86_64 Machine  │
│   (arm64)    │   4002     │  (separate hw)  │
│              │            │  - IB Gateway   │
│ Bot running  │            │  - Listening    │
│ (update .env)│            │    :4002        │
└──────────────┘            └─────────────────┘
```

**Setup Steps**:
1. **On x86 machine** (Windows/Linux/Mac):
   - Download IBKR Gateway from IBKR website
   - Install with default settings
   - Configure: API enabled, port 4002, socket clients allowed

2. **On Raspberry Pi**:
   - SSH: `ssh saladbar751@192.168.7.117`
   - Edit: `nano .env` → Change `IBKR_HOST=127.0.0.1` to `IBKR_HOST=<x86_ip>`
   - Example: `IBKR_HOST=192.168.7.100` (if x86 machine on same network)
   - Save & test: `python test_ibkr_connection.py`

**Pros**:
- ✅ Native x86_64 Gateway performance
- ✅ Multiple Pis can share one Gateway
- ✅ Clean separation of concerns
- ✅ Uses official IBKR binaries

**Alternatives** (if x86 hardware unavailable):
- **Option 2**: QEMU ARM emulation (complex, slow, not recommended for trading)
- **Option 3**: Deploy entire bot on x86_64 instead of Pi

See [SESSION_12_30_2025_SUMMARY.md](SESSION_12_30_2025_SUMMARY.md#-solutions-identified) for detailed options.

---

### **📋 NEXT STEPS**

**User Action Required** (before resuming deployment):
1. Procure or identify an x86_64 machine (Windows, Linux VM, or existing computer on home network)
2. Install IBKR Gateway on that x86 machine
3. Verify Gateway listening on port 4002

**Then Resume** (automation ready, just needs Gateway accessible):
- Step 10: Gateway port verification
- Step 11: IBKR API connectivity test
- Step 12: End-to-end bot validation
- Step 14: Deployment runbook finalization
- Step 16: Final QA sign-off

---

### **📊 QA READINESS**

**✅ Code Review Ready Now**:
- 116/116 tests passing
- Comprehensive safety guards (daily loss limits, position sizing, market hours)
- Thread-safe operations
- Complete documentation

**⏳ Deployment Testing Blocked**:
- Gateway availability required (architecture issue resolved by x86 setup)
- All test procedures documented in [docs/QA_READINESS_CHECKLIST.md](docs/QA_READINESS_CHECKLIST.md)
- Will resume immediately once x86 Gateway accessible

---

### **📋 REMAINING DEPLOYMENT STEPS (10-16)**

**After Gateway Resolution**:
- **Step 10**: Deploy IBKR Gateway container on Pi - Verify port 4002 listening with `ss -tln | grep 4002`
- **Step 11**: Test IBKR connectivity from Pi - Run `make ibkr-test`, confirm SPY quote fetch succeeds
- **Step 12**: Run bot with dry_run=true - Execute `python -m src.bot.app`, monitor logs for 1-2 cycles
- **Step 13**: Test Discord alerts (if configured) - Trigger sample alert, verify message in Discord channel
- **Step 14**: Create Pi deployment runbook - Document exact commands from steps 1-16 for future deploys
- **Step 15**: Optional: Test bracket order creation - Run `make ibkr-test-whatif`, verify TP/SL placement
- **Step 16**: Final: Document results and next steps - Update QA findings, determine live trading readiness

---

### **🐛 SESSION CHALLENGES & RESOLUTIONS**

**Challenge 1**: SSH Authentication Failure
- **Error**: "Permission denied (publickey,password)" with username "pi"
- **Root Cause**: Raspberry Pi Imager custom username "saladbar751" overrode default "pi"
- **Resolution**: Used correct username from Imager configuration
- **Learning**: Imager custom username replaces Pi OS default account

**Challenge 2**: Python 3.11 Unavailable in Debian Trixie
- **Error**: `apt-get install python3.11` failed with "Unable to locate package"
- **Root Cause**: Debian Trixie ships Python 3.13 by default, older versions not in repos
- **Resolution**: Installed pyenv, built Python 3.11.9 from source with full build deps
- **Learning**: Newer Debian releases require pyenv for specific Python versions

**Challenge 3**: pandas-ta Installation Failures
- **Error**: "Could not find version that satisfies requirement" for pandas-ta
- **Root Cause**: Package unavailable on piwheels for arm64, recent PyPI versions require Python >=3.12
- **Resolution**: Codebase grep revealed pandas-ta unused, removed from requirements.txt
- **Learning**: Always validate dependencies are actually imported before troubleshooting installations

**Challenge 4**: Docker Not Installed
- **Error**: `docker: command not found` when attempting GHCR login
- **Root Cause**: Fresh OS installation doesn't include Docker Engine
- **Resolution**: Installed via Docker convenience script, added user to docker group
- **Learning**: Docker requires explicit installation and group membership on Raspberry Pi OS

**Challenge 5**: IBKR Gateway Container Crash Loop
- **Error**: "Offline TWS/Gateway version 1015 not installed: can't find jars folder"
- **Root Cause**: Docker images expect Gateway binaries at /home/ibgateway/Jts but jars missing
- **Status**: **UNRESOLVED** - All tested public images fail with same error
- **Learning**: Public IBKR Gateway Docker images may have incomplete builds; manual installation more reliable

---

### **📁 KEY FILE CHANGES (Session 12/29/2025)**

**Files Modified**:
1. **requirements.txt**: Removed `pandas-ta` line (unused dependency unavailable for Python 3.11)
2. **docker-compose.gateway.yml**: Changed image from `ghcr.io/gyrasol/ibkr-gateway:latest` to `ghcr.io/gnzsnz/ib-gateway:stable`
3. **docs/STEP_1_FLASH_OS.md**: Created comprehensive OS flashing guide (9 substeps)

**Files Created on Pi**:
- `~/ibkr-options-bot/.env` - IBKR credentials and configuration (chmod 600)
- `~/ibkr-options-bot/.venv/` - Python 3.11.9 virtual environment with all dependencies

**Git Status**:
- Local Windows copy has modifications (requirements.txt, docker-compose.gateway.yml, docs/)
- Pi remote copy has same modifications plus .env (not tracked)
- Need to stage, commit, and push local changes to sync main branch

---

### **🔧 TECHNICAL ENVIRONMENT SNAPSHOT**

**Pi Hardware & OS**:
- **Model**: Raspberry Pi 4
- **Hostname**: Jeremiah
- **IP**: 192.168.7.117
- **OS**: Debian GNU/Linux Trixie (not Bookworm as expected)
- **Kernel**: Linux 6.12.47+rpt-rpi-v8 (64-bit arm64)
- **Username**: saladbar751 (custom, not default "pi")

**Python Environment**:
- **System Python**: 3.13.5 (Trixie default)
- **Bot Python**: 3.11.9 (pyenv-managed, in .venv)
- **Package Manager**: pip 25.3, piwheels mirror active
- **Key Packages**: ib-insync 0.9.86, pydantic 2.12.5, pandas 2.3.3, numpy 2.4.0

**Docker Setup**:
- **Engine**: 29.1.3
- **Compose**: CLI plugin v2.27.1
- **Registry**: Logged into ghcr.io with GitHub PAT (read:packages scope)
- **Test**: hello-world container ran successfully

**IBKR Configuration**:
- **Mode**: Paper trading
- **Port**: 4002
- **Client ID**: 101
- **Username**: saladbar751
- **Password**: _?gB,2_ZkR?Le84 (stored in .env)
- **Timezone**: TZ=America/New_York (in .env for bot market hours)

**System Timezone**:
- **Strategy**: Kept system timezone as user-configured (non-ET)
- **Bot Timezone**: TZ=America/New_York set in .env for accurate market hours (9:30-16:00 ET)

---

### **🎯 DEPLOYMENT SUCCESS CRITERIA**

**Before proceeding to Step 12 (bot validation)**:
- [ ] Gateway container running or manual Gateway process active
- [ ] Port 4002 listening: `ss -tln | grep 4002` shows LISTEN
- [ ] IBKR API responding: `python test_ibkr_connection.py --host 127.0.0.1 --port 4002` succeeds
- [ ] SPY market data fetched (confirms API permissions and connectivity)
- [ ] No container crash loops in `docker ps` or `docker compose logs`

**Configuration Verification**:
- [ ] `dry_run: true` in configs/settings.yaml (CRITICAL - prevents real orders)
- [ ] `.env` file contains IBKR_USERNAME, IBKR_PASSWORD, TZ=America/New_York
- [ ] Virtual environment activated: `source ~/ibkr-options-bot/.venv/bin/activate`
- [ ] All dependencies importable: `python -c "import ib_insync, pandas, numpy; print('OK')"`

---

### **📚 DOCUMENTATION CREATED**

**New Deployment Guide**:
- **docs/STEP_1_FLASH_OS.md** - Complete OS flashing walkthrough (9 substeps with troubleshooting)
  - Raspberry Pi Imager installation
  - Device and OS selection guidance
  - SSH and timezone pre-configuration
  - Time estimates and verification steps

**Updated Files**:
- **README.md** - This comprehensive session summary (replaced "Start Here" section)
- **.github/copilot-instructions.md** - Already contains full architecture guidance

**Pending Documentation** (Step 14):
- Pi deployment runbook with copy-paste commands
- Troubleshooting section for common Pi deployment issues
- Gateway resolution decision tree (Docker vs manual)

---

### **⏱️ TIME ESTIMATES (Remaining Work)**

**Gateway Resolution (Critical Path)**:
- Option A (try different image): 15-30 minutes
- Option B (manual install): 45-60 minutes  ← **RECOMMENDED**
- Option C (custom image): 60-90 minutes

**Post-Gateway Steps**:
- Connectivity testing: 5-10 minutes
- Bot dry-run validation: 10-15 minutes
- Discord alert testing: 5 minutes (if configured)
- Runbook documentation: 20-30 minutes
- Bracket order testing: 10 minutes (optional)

**Total Remaining**: 90-150 minutes (depending on Gateway path chosen)

---

### **🚨 SAFETY REMINDERS**

**Before Any Bot Execution**:
- ✅ Verify `dry_run: true` in configs/settings.yaml
- ✅ Confirm IBKR_PORT=4002 (paper trading port, not 4001 live port)
- ✅ Start with single symbol only (SPY) in configs/settings.yaml
- ✅ Monitor logs continuously during first 3 cycles: `tail -f logs/bot.log`
- ✅ Have `Ctrl+C` ready to interrupt if unexpected behavior occurs

**Never Bypass**:
- Daily loss guards (`should_stop_trading_today()`)
- Position sizing limits (`position_size()`)
- Liquidity filters (`is_liquid()`)
- Market hours checks (`is_rth()`)

---

### **💡 QUICK REFERENCE COMMANDS**

**Pi SSH Access**:
```bash
ssh saladbar751@192.168.7.117
cd ~/ibkr-options-bot
source .venv/bin/activate
```

**Gateway Management**:
```bash
# Docker-based (if using containers)
docker compose -f docker-compose.gateway.yml up -d       # Start
docker compose -f docker-compose.gateway.yml logs -f     # Monitor
docker compose -f docker-compose.gateway.yml down        # Stop
docker ps | grep gateway                                  # Check status

# Manual Gateway (if installed directly)
~/start_gateway.sh                                        # Start
ps aux | grep ibgateway                                  # Check process
ss -tln | grep 4002                                      # Verify port
```

**Bot Operations**:
```bash
# Test connectivity first
python test_ibkr_connection.py --host 127.0.0.1 --port 4002 --timeout 10

# Run bot (dry_run mode)
python -m src.bot.app

# Monitor logs in separate terminal
tail -f logs/bot.log
tail -f logs/bot.jsonl  # Structured logs for parsing
```

**Troubleshooting**:
```bash
# Check environment variables
set -a; . ./.env; set +a
env | grep IBKR_

# Verify Python packages
python -c "import ib_insync, pandas, numpy; print('Dependencies OK')"

# Test Docker connectivity
docker run --rm hello-world

# Check for port conflicts
sudo ss -tln | grep 4002
```

---

### **🔄 GIT WORKFLOW (End of Session)**

**Stage and Commit Local Changes**:
```bash
# From Windows local repository
cd "C:\Users\tasms\my-new-project\Trading Bot\ibkr-options-bot"

# Review changes
git status
git diff requirements.txt
git diff docker-compose.gateway.yml

# Stage all changes
git add requirements.txt docker-compose.gateway.yml docs/STEP_1_FLASH_OS.md README.md

# Commit with descriptive message
git commit -m "feat(pi): Complete Pi deployment Phase 1 - Steps 1-8

- Remove pandas-ta from requirements.txt (unused, unavailable for Python 3.11)
- Update docker-compose.gateway.yml to gnzsnz/ib-gateway:stable
- Add comprehensive OS flashing guide (docs/STEP_1_FLASH_OS.md)
- Update README with session 12/29/2025 progress and next steps

Completed: OS flash, SSH config, Python 3.11.9 via pyenv, dependencies, Docker install
Blocker: Gateway container crash loop (jars folder missing in all tested images)
Next: Manual Gateway installation recommended (Option B)"

# Push to main branch
git push origin main
```

**Verify Remote Sync**:
```bash
# Check GitHub repository shows latest commit
git log -1 --oneline
git remote -v
```

---

## **Architecture Overview**

This bot implements a **protocol-based broker architecture** with:
- **Broker Abstraction**: Protocol interface allowing StubBroker (testing) and IBKRBroker (production)
- **Strategy Layer**: Scalp rules and whale detection with configurable parameters
- **Risk Management**: Position sizing, daily loss guards, thread-safe operations
- **Orchestration**: Scheduler with cron-like execution, structured logging

**Key Files**:
- `src/bot/app.py` - Main application entry point with startup validation
- `src/bot/broker/ibkr.py` - IBKR connectivity and order management
- `src/bot/strategy/scalp_rules.py` - Primary trading strategy (RSI + volume)
- `src/bot/strategy/whale_rules.py` - Volume spike detection (3-day debounce)
- `configs/settings.yaml` - Unified configuration management (Pydantic)
- `.github/copilot-instructions.md` - AI agent guidance (comprehensive patterns)

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
