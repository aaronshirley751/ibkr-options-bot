# Extended Dry-Run Test - Session 2026-01-07

**Status**: ✅ INITIATED  
**Start Time**: 2026-01-07 12:10 UTC  
**Target Duration**: 180 minutes (3 hours)  
**Test Mode**: dry_run=true (no real orders)  
**Gateway**: 192.168.7.205:4001 (live account)  

## Test Objectives

1. ✅ Validate bot stability over extended runtime
2. ✅ Monitor memory usage and resource consumption
3. ✅ Collect signal statistics (BUY/SELL/HOLD distribution)
4. ✅ Test Discord webhook notifications
5. ✅ Verify log rotation and persistence
6. ✅ Ensure no crash or hang conditions

## Configuration

- **Dry-Run**: Enabled (orders logged, not executed)
- **Symbols**: SPY (single symbol for baseline)
- **Interval**: 300s (5 minutes) between cycles
- **Risk Limit**: 15% daily loss guard active
- **Alerts**: Discord webhook enabled

## Monitoring

- **Memory Sampling**: Every 5 minutes
- **Log Level**: INFO + DEBUG
- **Output Files**:
  - `logs/test_YYYYMMDD_HHMMSS.log` - Main bot log
  - `logs/memory_*.log` - Memory usage history
  - `logs/summary_*.txt` - Test summary

## Expected Results

- **Cycle Completions**: ~36 cycles (180 min ÷ 5 min interval)
- **Signal Distribution**: Mix of BUY/SELL/HOLD based on market conditions
- **Memory Stability**: <200MB on Pi, <300MB on dev machine
- **No Errors**: Zero crashes, connection drops handled gracefully

## Analysis Commands

```bash
# After test completes, run:
python scripts/analyze_logs.py --bot-log logs/test_*.log --output logs/report.txt

# View memory trend:
tail -n +2 logs/memory_*.log | awk '{print $6}' | sort -n
```

## Contingencies

- If bot crashes: Systemd service (`scripts/ibkr-bot.service`) provides auto-restart on Pi
- If memory spikes: Check for broker reconnection loops or options chain bloat
- If signals stop: Verify IBKR connection; check `logs/test_*.log` for errors

## Next Steps After Test

1. Analyze logs and generate summary
2. Peer review code changes
3. If successful: Authorize paper trading decision
4. If issues: Debug and iterate

---

## Actual Results (2026-01-07)

- Connected to 192.168.7.205:4001 with clientId 213; option chain returned 34 expirations/427 strikes.
- First cycle completed; dry-run order simulated; emulated OCO started.
- Subsequent cycles: `reqHistoricalData` timeouts → scheduler logged "Skipping: insufficient bars" (no bars >=30).
- Run ended with exit code 130 after repeated timeouts; no crashes.

## Follow-Ups

1. Add backoff/early-exit when historical requests time out repeatedly (or adjust duration/use_rth).
2. Optional flag to clear current-day loss guard at startup for dry-run/off-hours: `risk.reset_daily_guard_on_start` (default false).
3. Re-run during RTH after implementing the above and recheck with `scripts/analyze_logs.py --bot-log <file>`.
