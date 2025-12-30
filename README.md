# ibkr-options-bot

Lightweight scaffold for an IBKR options trading bot with clean layers (broker, data, strategy, execution, scheduler) and Pydantic-driven config. See [.github/copilot-instructions.md](.github/copilot-instructions.md) for architecture notes.

---

## Session Summary (2025-12-30)
- Gateway now runs on Windows x86_64 at 192.168.7.205:4002; Raspberry Pi bot connects successfully in dry_run mode
- Connection stability fixes: broker connect creates a dedicated event loop in its worker thread and falls back to sync connect when needed
- Option secdef lookup fixed by requesting the underlying first; historical request duration adjusted to 1800 S for short tests
- Remaining noise: IB error 321 on historical bars due to data permissions/duration; bot skips symbols when bars are insufficient

## Errors, Root Causes, and Fixes
- Missing underlying conId for option security definition
  - Root cause: reqSecDefOptParams called without first resolving the underlying contract
  - Fix: request the underlying in test_ibkr_connection.py and reuse its conId for the secdef query
- Coroutine/event loop warnings and failed reconnects
  - Root cause: ib_insync.connect called from a worker thread without an event loop bound to the thread
  - Fix: in src/bot/broker/ibkr.py create and set a new event loop in the connect thread, then use sync connect fallback; improved exception logging
- Historical data duration validation errors
  - Root cause: invalid duration string for short windows
  - Fix: use "1800 S" for quick connectivity checks in test_ibkr_connection.py; warning 321 persists when data permissions are limited but is non-blocking

## Current State
- Connectivity: Pi talks to Windows Gateway at 192.168.7.205:4002 with clientId=101; host override works
- Bot mode: dry_run true; scheduler skips symbols when fewer than 30 bars are returned
- Tests: full test suite previously passing (116/116); not rerun after this README-only update
- Repo: main is clean; this commit documents the latest session

## START HERE NEXT SESSION
- Verify Gateway: ensure Windows IBKR Gateway is running, API enabled, listening on 192.168.7.205:4002 (paper), and client connections allowed
- Connectivity check: from Pi run python test_ibkr_connection.py --host 192.168.7.205 --port 4002 --timeout 10 and confirm quotes return
- Run bot (dry): python -m src.bot.app and watch logs for reconnects and historical warnings; expect skips if bars < 30
- Address warning 321 if desired: shorten historical window in scheduler or confirm market data permissions/delayed data availability
- Prepare for paper validation: once data flows, enable bracket/TP-SL checks and document results for QA

## Quick Commands
- Activate venv (Windows): .venv\\Scripts\\activate
- Connectivity test: python test_ibkr_connection.py --host 192.168.7.205 --port 4002 --timeout 10
- Run bot (dry): python -m src.bot.app
- Tail logs: tail -f logs/bot.log

## Key Files
- Broker connect logic: [src/bot/broker/ibkr.py](src/bot/broker/ibkr.py)
- Scheduler orchestration: [src/bot/scheduler.py](src/bot/scheduler.py)
- Connectivity test harness: [test_ibkr_connection.py](test_ibkr_connection.py)
- Settings defaults: [configs/settings.yaml](configs/settings.yaml)

## Safety Checklist
- Ensure dry_run remains true until paper trading is explicitly approved
- Use paper port 4002 (not live 4001)
- Keep symbols minimal (start with SPY) while validating connectivity
- Monitor first cycles live and be ready to stop with Ctrl+C if behavior is unexpected

