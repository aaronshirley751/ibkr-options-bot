# ibkr-options-bot

Lightweight scaffold for an IBKR options trading bot with clean layers (broker, data, strategy, execution, scheduler) and Pydantic-driven config. See [.github/copilot-instructions.md](.github/copilot-instructions.md) for architecture notes.

---

## Session Summary (2025-12-31)
**Complete end-to-end validation achieved: Bot connects to Gateway, loads account data, fetches historical bars, and runs stable scheduler cycles.**

### Major Accomplishments
1. **Gateway Remote Access Enabled** (2025-12-31 ~10:00 UTC)
   - Windows IBKR Gateway reconfigured to accept remote client connections
   - Verified paper trading mode (port 4002) accessible from Raspberry Pi at 192.168.7.205:4002
   - Account connection: DUM490080 with $1,013,348.83 net liquidation

2. **Settings Configuration Fixed** (2025-12-31 ~11:30 UTC)
   - Corrected hardcoded host from 127.0.0.1 to 192.168.7.205 in configs/settings.yaml on Pi
   - Environment variable override (BROKER__HOST) working as fallback for flexibility

3. **Historical Data Duration Bug Fixed** (2025-12-31 ~11:45 UTC)
   - **Root Cause**: Duration parameter "60 M" in ibkr.py interpreted as 60 months by IBKR API
   - **Error**: IB Error 321 "Historical data request for durations longer than 12 months must be made in years"
   - **Solution**: Changed default duration from "60 M" to "3600 S" (3600 seconds = 1 hour)
   - **Result**: ✅ Bot now successfully fetches 46 historical 1-minute bars per cycle
   - **Commit**: 88879d1 "fix: change historical data duration from '60 M' to '3600 S' to fix IBKR error 321"

4. **Bot Execution Validation** (2025-12-31 ~12:00 UTC)
   - Bot running continuously on Pi with stable 5-minute scheduler cycles
   - Account data loads correctly on connection
   - Heartbeats stable (~3 minute intervals)
   - No crash on error handling (graceful skip when data unavailable)

### Data Flow Verified (11:56 UTC log capture)
```
Request:   3600 S duration (1 hour window) + 1-minute bars
Response:  46 bars from 11:55-12:40 US/Eastern with complete OHLCV data
Status:    ✅ SUCCESS - bars flow through pipeline for strategy evaluation
```

## Errors, Root Causes, and Fixes (Session 2025-12-31)

### Issue 1: Event Loop Missing in Worker Thread
- **Root Cause**: ib_insync.connect() called from scheduler thread without bound event loop
- **Error**: `RuntimeError: There is no current event loop in thread 'ThreadPoolExecutor-...'`
- **Status**: ✅ FIXED (previous session, commit be8cef7)
- **Solution**: broker.connect() now creates dedicated event loop in worker thread

### Issue 2: Gateway Remote Connections Blocked
- **Root Cause**: Windows IBKR Gateway configured for localhost connections only
- **Error**: `TimeoutError()` when Pi tried to connect to 192.168.7.205:4002
- **Status**: ✅ FIXED (2025-12-31 ~10:15 UTC)
- **Solution**: User updated Gateway settings to "Allow API connections from remote IP addresses"

### Issue 3: Incorrect Host in Settings
- **Root Cause**: configs/settings.yaml hardcoded host to 127.0.0.1 on Pi
- **Error**: Bot connected to localhost instead of remote Gateway
- **Status**: ✅ FIXED (2025-12-31 ~11:30 UTC, verified via ssh sed)
- **Solution**: Updated settings.yaml broker.host from "127.0.0.1" to "192.168.7.205"

### Issue 4: Historical Data Duration Format ⭐ CRITICAL FIX
- **Root Cause**: Duration parameter "60 M" sent to IBKR API; API interprets "M" as months for durations > 12M
- **Error**: IB Error 321 "Historical data request for durations longer than 12 months must be made in years"
- **Status**: ✅ FIXED (2025-12-31 ~11:45 UTC)
- **Solution**: Changed [src/bot/broker/ibkr.py](src/bot/broker/ibkr.py) line 313 from `"60 M"` to `"3600 S"`
- **Evidence**: Bot Test Log 3 shows successful bar fetch at 11:56:00 with 46 bars returned

## Current State (2025-12-31 Post-Fix)
- **Connectivity**: ✅ Pi → Windows Gateway (192.168.7.205:4002) stable and verified
- **Account Data**: ✅ Loads correctly, heartbeats every ~3 minutes
- **Historical Bars**: ✅ 46 bars/cycle fetched successfully (1-minute resolution, 3600S window)
- **Scheduler**: ✅ Runs 5-minute cycles with SPY symbol in dry_run mode
- **Error Handling**: ✅ Graceful (skips symbols if data unavailable, doesn't crash)
- **Data Flow**: ✅ Bars available for strategy evaluation (scalp_rules, whale_rules)
- **Order Execution**: ⏳ Dry-run mode active (no real orders); ready for paper trading validation

## START HERE NEXT SESSION

### Session 2025-01-01 - Paper Trading Validation Phase

**Goal**: Validate complete data flow and confirm strategy signals generate correctly with real market data

#### Quick Startup Checklist
1. **Gateway Verification** (5 min)
   ```bash
   # Windows: Start IBKR Gateway, verify port 4002 and remote connections enabled
   # Test from Windows:
   python test_ibkr_connection.py --host 127.0.0.1 --port 4002 --timeout 10
   ```

2. **Pi Connectivity** (5 min)
   ```bash
   ssh saladbar751@192.168.7.117
   cd ~/ibkr-options-bot && source .venv/bin/activate
   python test_ibkr_connection.py --host 192.168.7.205 --port 4002 --timeout 10
   # Expected: Connection successful, 46 bars returned
   ```

3. **Bot Startup** (2 min)
   ```bash
   # On Pi
   cd ~/ibkr-options-bot && python -m src.bot.app
   # Expected: Account loads, heartbeats every ~3 min, 46 bars/cycle
   ```

4. **Log Monitoring** (10 min - first cycle)
   ```bash
   # On Pi (separate terminal)
   tail -50 logs/bot.log | grep -E "cycle|signal|insufficient|order|ERROR"
   # Expected: See cycle start/end, "insufficient bars" or signal decisions
   ```

#### Validation Steps

**Step 1: Verify Data Flow (10 min)**
- Bot runs 5-minute cycles continuously
- Each cycle: fetches 46 bars → evaluates strategy → logs signal or skip
- Account balance loads correctly ($1,013,348.83 baseline)
- No crashes or event loop errors in logs

**Step 2: Confirm Strategy Signals** (20 min - 4 cycles)
- Monitor logs for scalp_rules signal evaluation (BUY/SELL/HOLD confidence scores)
- If market conditions trigger signals, verify confidence calculation is correct
- Check whale_rules debounce logic works (3-day per-symbol cooldown)
- Expected output: `[symbol=SPY, signal=HOLD, confidence=0.0]` or similar

**Step 3: Test Dry-Run Order Creation** (10 min - conditional)
- If signal triggers and dry_run=true, verify:
  - Log shows "Dry-run: Would place order..." instead of actual order
  - No real orders appear in IBKR account
  - Thread safety is maintained (no concurrent order conflicts)
  - Bracket order parameters logged correctly (entry, TP%, SL%)

**Step 4: Monitor Scheduler Stability** (ongoing)
- Run for 30+ minutes without stopping
- Verify no memory leaks (check Pi cpu/memory with `top`)
- Heartbeats continue every ~3 minutes
- No reconnect spam in logs
- Symbols are processed in ThreadPoolExecutor without deadlock

#### Common Issues & Quick Fixes

| Issue | Check | Fix |
|-------|-------|-----|
| Bot won't start | `python -c "import src.bot.app"` | Check Python 3.11, venv activated, deps installed |
| Timeout on 192.168.7.205 | Gateway running? Remote connections enabled? | Restart Gateway on Windows |
| "Insufficient bars" constantly | Check bar count in logs | Expected if < 30 bars; market may be quiet |
| "Error 321" returns | Update ibkr.py duration? | Check commit 88879d1; should be "3600 S" |
| Signals never trigger | Check RSI/EMA logic | Review scalp_rules thresholds; adjust if market is flat |

#### Next Actions After Validation

- **If all tests pass**: Update this README with validation timestamp and move to Phase 2 (paper trading with real account)
- **If data flow blocked**: Check logs for specific errors; grep for "ERROR\|Exception\|321" and cross-reference copilot-instructions.md
- **If signals trigger**: Document signal examples and confidence scores; prepare for bracket order testing
- **If signals never trigger**: Review market conditions during test window; consider adjusting scalp_rules thresholds or extending test duration

#### Key Metrics to Record

After 1 hour of stable running, capture:
- Number of complete cycles: `grep -c "Processing symbol" logs/bot.log`
- Signal decisions: `grep "signal=" logs/bot.log | tail -10`
- Error count: `grep -c "ERROR" logs/bot.log`
- Bar fetch success: `grep "bars returned" logs/bot.log | wc -l`

#### Session Notes
- Dry-run mode **remains true** until explicitly approved for paper trading
- Paper port is **4002** (not 4001 live); never switch without explicit user approval
- If restarting bot frequently: stop Pi bot with `pkill -f "python -m src.bot.app"` to clean up
- Logs rotate at 10MB; full history in `logs/bot.jsonl` (JSON for parsing)

---

## Previous Session Notes (2025-12-30)
See git history for detailed per-issue fixes. Key commits:
- `be8cef7`: Event loop fix in broker.connect
- `1337eb3`: Session summary doc
- `88879d1`: Historical data duration fix (3600 S)

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

