# Phase 1 production readiness and alignment findings

Date: 2025-12-11
Scope: Consolidated outcomes from the latest review of architecture, risk controls, execution, and deployment readiness for Phase 1 (single-process, paper trading on Raspberry Pi or equivalent).

## Overall readiness
- Status: GO for Phase 1 paper trading on Pi, pending IBKR Gateway connectivity validation on target hardware.
- Confidence drivers: 7/7 tests passing; deterministic StubBroker coverage; bracket + OCO execution implemented; daily loss guard persisted; debounce logic verified.
- Known constraints: single-process only; in-memory whale debounce resets on restart; assumes <= a few concurrent symbols; gateway availability is the gating factor.

## Key findings
### Configuration pattern
- Entry point loads typed Pydantic Settings from YAML + env; scheduler intentionally receives a dict via `settings.model_dump()` for flexible `get()` access.
- Nested models: Broker, Risk, Schedule, Options, Monitoring. Env overrides use `__` delimiter (e.g., `RISK__MAX_DAILY_LOSS_PCT`).

### Strategy layer
- Scalp (1-min bars): BUY/SELL/HOLD with RSI/VWAP/EMA gating; requires >=30 bars.
- Whale (60-min bars): BUY_CALL/BUY_PUT/HOLD with 20-day range + 1.5x volume; **3-day in-memory debounce per symbol**; resets on process restart.
- Signal schema: `{ "signal": BUY|SELL|HOLD (or BUY_CALL/BUY_PUT), "confidence": float, "reason": optional }`.

### Execution & orders
- Primary: IBKR native brackets built in `place_order` (parent + TP/SL children via OCA group).
- Fallback: `execution.emulate_oco` runs in a background thread (polls q.last every 5s; submits TP limit or SL market close).
- Liquidity guard: `is_liquid` enforces spread % and min volume before proceeding.

### Risk & sizing
- Position sizing: `floor(equity * max_risk_pct / (premium * stop_loss_pct))`, min 1.
- Daily loss guard: persists start-of-day equity in `logs/daily_state.json` (keyed by YYYY-MM-DD); survives restarts; guard triggers when loss >= max_daily_loss_pct.
- Take-profit/stop-loss: percent-of-premium inputs drive bracket/OCO levels.

### Orchestration & concurrency
- Scheduler interval: default 180s; RTH gate (09:30–16:00 ET).
- Concurrency: ThreadPoolExecutor (default max_workers=2; configurable); broker access serialized via `_with_broker_lock()` using broker `_thread_lock` if present else local `Lock()`.
- Data flow per symbol: fetch bars → `_to_df` → scalp (1m) → whale (60m resample) → action selection → option pick (weekly ATM/near) → quote premium → size → bracket/OCO submit → journal/log.

### Observability
- Logging: loguru (fallback to stdlib) with structured `.bind`; text + JSONL; rotation handled by loguru defaults.
- Files of interest: trade journaling, `logs/daily_state.json` for loss guard state.

## Gaps / constraints to carry forward
- Debounce not persistent across restarts (intentional for Phase 1); consider Redis if scaling beyond single process.
- Gateway connectivity on Pi not yet validated; blocker for true paper/live testing.
- Test coverage ~27%; focus areas: broker protocol integration, execution edge cases, whale rule variants.
- No distributed coordination; designed for single node/single process in Phase 1.

## Recommended next steps (pre-peer review)
1) Validate Gateway on Pi: run `scripts/test_gateway_options.sh`; then `make ibkr-test` against chosen gateway.
2) Dry-run to paper transition: confirm brackets + OCO behavior in paper with small symbols set; keep `dry_run` true until quotes verified.
3) Add tests: broker integration (StubBroker), execution edge cases (OCO triggers), whale rule scenarios (volume/price extremes).
4) Monitoring hooks: wire heartbeat/Slack/Telegram settings and validate outbound alerts.
5) Concurrency sanity: exercise `max_concurrent_symbols` >2 in StubBroker to validate lock/throughput.

## Alignment with stated goals
- Phase 1 goal (Pi, paper trading, stability/safety): aligned and ready pending gateway validation.
- Architecture matches roadmap: protocol-based broker, modular strategy/data/execution layers, risk-first controls, ready for containerization and CI/CD in Phase 2.
- Safety posture: daily loss guard persisted; TP/SL enforced; liquidity checks; in-memory debounce to prevent churn; dry_run default recommended for bring-up.

## Deployment readiness snapshot
- Code: ready for Phase 1 paper trading.
- Config: YAML + env overrides; dry_run on by default recommended.
- Infra: Docker compose files for gateway options; scripts for Pi setup; make targets for deps/tests/gateway.
- Blocker: IBKR Gateway accessibility on target host must be proven before live/paper execution.
