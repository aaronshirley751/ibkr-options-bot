# 🚀 START HERE - Next Session Quick Start Guide

## ✅ 2026-01-06 — Fast Checklist (Entitlement Follow‑Up)
IBKR support ticket submitted; subscriptions and API ACK show active. Use this checklist to re‑test quickly once IBKR confirms entitlements or after a backend refresh.

1) Re‑test quotes from Pi (new clientId)
```bash
ssh -i ~/.ssh/id_rsa saladbar751@192.168.7.117 "cd ~/ibkr-options-bot && source ~/.venv/bin/activate && python test_ibkr_connection.py --host 192.168.7.205 --port 4001 --client-id 187 --timeout 15"
```
- Expect non‑nan `last/bid/ask` and a populated `option_snapshot` (no `no_secdef`).

2) If quotes OK, run extended live validation (RTH)
```bash
ssh -i ~/.ssh/id_rsa saladbar751@192.168.7.117 "cd ~/ibkr-options-bot && source ~/.venv/bin/activate && timeout 3600 python -m src.bot.app"
```
- Success criteria: continuous bar flow, strategy decisions logged, no reconnect spam, `dry_run` order logs only.

3) If quotes still nan
- Note timestamp + `clientId`, capture `historical_1m` count and `stock_snapshot` fields.
- Reply to IBKR ticket referencing README 2026‑01‑06 summary and attach output.

4) Safety
- Keep `dry_run: true` until entitlements validated and strategy reviewed.

---

**Last Session:** January 2, 2026 at 4:15 PM ET  
**Next Session Target:** January 3, 2026 at 9:30 AM ET (market open)  
# 🚀 START HERE - Next Session Quick Start Guide (2026-01-07)

## Snapshot
- Extended dry-run (RTH) connected and ran one full cycle; subsequent cycles hit `reqHistoricalData` timeouts → “Skipping: insufficient bars”; exit code 130.
- Option chain and dry-run order path are good; main gap is historical data robustness during market hours.
- Gateway: 192.168.7.205:4001, clientId 213, `dry_run=true`.

## First Actions (next market session)
1) Optional: clear today’s loss guard (dry-run only)
```bash
python - <<'PY'
import json, datetime, pathlib
p=pathlib.Path('logs/daily_state.json')
data=json.loads(p.read_text()) if p.exists() else {}
3. **Propagation takes 15-30 minutes** → Be patient after acknowledgement submission
4. **Client IDs persist for ~60 seconds** → Increment for rapid testing
print('Cleared current-day loss guard')
PY
```

2) Run extended dry-run with monitoring (RTH)
```bash
BROKER__HOST=192.168.7.205 BROKER__PORT=4001 BROKER__CLIENT_ID=213 \
./scripts/start_extended_test.sh 180 192.168.7.205
```
- Watch for `reqHistoricalData: Timeout`; if repeated, stop early and adjust params (see step 3).

3) If timeouts persist, try one of:
- Set `use_rth=False` and/or `duration='7200 S'` in broker.historical_prices (code change needed).
- Reduce bar requirement temporarily (e.g., accept 10 bars) for diagnostics.
- Add backoff: after N consecutive timeouts, sleep longer or skip cycle.

4) Analyze log after run
```bash
python scripts/analyze_logs.py --bot-log logs/test_*.log
```

## Small Bot Tweaks to Implement
1. Historical data resilience: backoff/early-exit on repeated timeouts; consider longer duration or non-RTH fetch for resiliency.
2. Optional loss-guard auto-reset flag: `risk.reset_daily_guard_on_start: true` → clear today’s entry in `logs/daily_state.json` at startup (default false).

## Monitoring Tips
- Look for “Cycle decision” after the first cycle; if absent and only “Skipping: insufficient bars” appears, historical data is not arriving.
- Keep an eye on `logs/daily_state.json`; avoid resetting during live trading unless `dry_run`.

## Commands Reference
- Quick bot run (5 min):
```bash
BROKER__HOST=192.168.7.205 BROKER__PORT=4001 BROKER__CLIENT_ID=213 \
timeout 300 python -m src.bot.app
```
- View latest log:
```bash
ls -1t logs/test_*.log | head -1 | xargs tail -100
```
- Git status:
```bash
git status --short
```
5. **RTH guard active** → Bot only runs 9:30 AM - 4:00 PM ET
6. **Gateway restart helps** → Forces re-authentication and connection cleanup

---

## 📞 Support Resources

**IBKR Portal:** https://www.interactivebrokers.com/portal  
**Market Data Subscriptions:** Account Management → Settings → User Settings → Market Data Subscriptions  
**API Troubleshooting:** https://www.interactivebrokers.com/en/support/  

**Documentation:**
- Full session summary: `SESSION_2026-01-02_COMPLETE.md`
- Architecture guide: `.github/copilot-instructions.md`
- Testing guide: `docs/TESTING_OUTCOMES.md`
- Gateway setup: `docs/GATEWAY_QUICKSTART.md`

---

## 🔐 Safety Reminders

⚠️ **CRITICAL:** `dry_run: true` in `configs/settings.yaml` - DO NOT CHANGE without explicit decision  
⚠️ **Port 4001 = Live Account** - Real money environment (dry_run protects)  
⚠️ **All tests use dry_run** - No real orders placed during validation  

---

## 🎯 Decision Point: Production Deployment

**After successful validation, decide:**
1. **Continue dry_run testing** - More stability validation (recommended)
2. **Enable live trading** - Change `dry_run: false` (requires explicit decision + review)

**Before live trading:**
- [ ] Review all risk settings (max_daily_loss_pct, max_risk_pct_per_trade)
- [ ] Validate stop-loss and take-profit percentages
- [ ] Test bracket order execution on small position
- [ ] Set up monitoring alerts (Slack/Telegram)
- [ ] Document rollback procedure
- [ ] Verify account funding sufficient for position sizes

---

**🚀 Ready to Start? Run Step 1 above and validate subscription status!**

**Questions? See `SESSION_2026-01-02_COMPLETE.md` for comprehensive details.**
