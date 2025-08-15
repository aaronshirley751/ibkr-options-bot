# ibkr-options-bot

Lightweight scaffold for an IBKR options trading bot.

Structure and goals are in the repository root. This project is a starting point and intentionally minimal — add credentials to `.env` and tune `configs/settings.yaml` before running.

Quickstart

1. Create a Python 3.11+ virtual environment and activate it.
2. Install requirements:

```bash
python -m pip install -r requirements.txt
```

3. Copy `.env.example` -> `.env` and fill in IBKR credentials.
4. Run tests:

```bash
python -m pytest -q
```

Files of interest: `src/bot/app.py`, `src/bot/broker/ibkr.py`, `configs/settings.yaml`.

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
