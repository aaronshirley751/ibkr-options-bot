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
**Current State:** Bot infrastructure ready, waiting for market data subscription activation

---

## ⚡ 60-Second Context Refresh

**What We Accomplished:**
1. ✅ Fixed event loop threading bug (commit f9ed836) - 20-min test passed
2. ✅ Migrated from paper (4002) to live account (4001) with `dry_run=true` safety
3. ✅ Purchased market data subscriptions ($4.50/month): Network B, Network C, OPRA
4. ✅ Submitted IBKR API acknowledgement at 4:15 PM ET
5. ✅ SSH key authentication working (passwordless)

**What's Blocking:**
- ⏳ Market data API acknowledgement propagating (15-30 min wait from 4:15 PM)
- ⏳ Error 10089 "Requested market data requires additional subscription" still present
- ⏳ Real-time data not flowing yet (bid/ask/last all `nan`)

**Expected Resolution:** Acknowledgement should be active by next session

---

## 🎯 First 5 Minutes - Critical Path

### Step 1: Verify Market Data Subscriptions Active (2 min)

**Quick Test:**
```bash
ssh -i ~/.ssh/id_rsa saladbar751@192.168.7.117 "cd ~/ibkr-options-bot && source ~/.venv/bin/activate && python test_ibkr_connection.py --host 192.168.7.205 --port 4001 --client-id 160 --timeout 15 2>&1 | grep -E '(Error 10089|last|bid|ask)'"
```

**Success Criteria:**
- ✅ No "Error 10089" in output
- ✅ `'last': <number>` (not `nan`)
- ✅ `'bid': <number>` (not `nan`)  
- ✅ `'ask': <number>` (not `nan`)

**If Still Blocked:**
1. Check IBKR Account Management → Market Data Subscriptions → verify "Active"
2. Restart Gateway to force re-authentication
3. Wait additional 15 minutes for propagation
4. Contact IBKR support if still blocked after 60+ minutes

---

### Step 2: Run Bot and Validate Real-Time Bars (3 min)

**Command:**
```bash
ssh -i ~/.ssh/id_rsa saladbar751@192.168.7.117 "cd ~/ibkr-options-bot && source ~/.venv/bin/activate && timeout 300 python -m src.bot.app 2>&1 | head -100"
```

**Success Criteria:**
- ✅ "Broker reconnected successfully" in logs
- ✅ No "Error 10089" 
- ✅ "Cycle decision" logged (strategy executed)
- ✅ No "reqSecDefOptParams returned empty chain" (options data available)

**Expected Output (Success):**
```
2026-01-03 09:31:00 | INFO | Broker reconnected successfully
2026-01-03 09:31:05 | INFO | Cycle decision
2026-01-03 09:31:06 | INFO | Strategy signal: BUY (confidence: 0.75)
```

---

## 🔧 Configuration Status

### Current Settings (`configs/settings.yaml`)
```yaml
broker:
  host: "192.168.7.205"
  port: 4001          # Live account
  client_id: 101      # Default restored
  read_only: false

dry_run: true         # ⚠️ SAFETY ENABLED - NO REAL ORDERS

symbols:
  - "SPY"             # Default restored

schedule:
  interval_seconds: 300
  max_concurrent_symbols: 1
```

### Network Setup
- Windows Gateway: 192.168.7.205:4001 (live account)
- Raspberry Pi: 192.168.7.117
- SSH: `ssh -i ~/.ssh/id_rsa saladbar751@192.168.7.117`

---

## 📋 Session Checklist

### Phase 1: Validate Infrastructure (15 min)
- [ ] Verify Error 10089 resolved
- [ ] Confirm real-time bars flowing (60+ bars, not 15-30)
- [ ] Test options chain returns data (`reqSecDefOptParams` successful)
- [ ] Check bid/ask/last prices populate (not `nan`)

### Phase 2: Extended Stability Test (45 min)
- [ ] Run bot for 1 hour during market hours
- [ ] Monitor for crashes or connection drops
- [ ] Verify strategy signals generate (`scalp_signal()`, `whale_rules()`)
- [ ] Check logs for errors or warnings

### Phase 3: Strategy Validation (30 min)
- [ ] Confirm scalp signals fire on QQQ/SPY movement
- [ ] Validate whale rules detect volume spikes
- [ ] Test 3-day debounce prevents rapid signals
- [ ] Review confidence scoring (0.0-1.0 range)

### Phase 4: Order Management Test (30 min)
- [ ] Verify position sizing calculations
- [ ] Test bracket order creation (take-profit/stop-loss)
- [ ] Monitor OCO emulation threads
- [ ] Confirm dry_run prevents real orders

### Phase 5: Documentation & Commit (30 min)
- [ ] Update README with live account migration
- [ ] Document market data setup process
- [ ] Commit all changes with descriptive messages
- [ ] Push to remote repository
- [ ] Tag release: `v0.2.0-live-data-ready`

---

## 🚨 Troubleshooting Quick Reference

### Error 10089 Still Present
**Cause:** API acknowledgement not propagated yet  
**Fix:** 
1. Restart Gateway
2. Wait 15 more minutes
3. Verify subscriptions show "Active" in portal
4. Check for pending agreements in Account Settings

### Client ID Already in Use (Error 326)
**Cause:** Previous connection still active in Gateway  
**Fix:** Increment client_id in settings.yaml (e.g., 101 → 105)

### Empty Options Chain
**Cause:** Linked to Error 10089 or after-hours  
**Fix:** Resolve subscription issue first, test during market hours (9:30 AM - 4:00 PM ET)

### Bot Exits Immediately
**Cause:** RTH guard (market hours check) or crash  
**Fix:** 
1. Check time: Must be 9:30 AM - 4:00 PM ET
2. View logs: `ssh -i ~/.ssh/id_rsa saladbar751@192.168.7.117 "tail -50 ~/ibkr-options-bot/logs/bot.log"`

### Gateway Connection Timeout
**Cause:** Gateway not running or IP restrictions  
**Fix:**
1. Verify Gateway running on Windows
2. Check Trusted IPs includes Pi: 192.168.7.117
3. Ensure "Allow localhost only" unchecked
4. Test port: `nc -zv 192.168.7.205 4001`

---

## 🔑 Essential Commands

### Test Subscription Status
```bash
ssh -i ~/.ssh/id_rsa saladbar751@192.168.7.117 "cd ~/ibkr-options-bot && source ~/.venv/bin/activate && python test_ibkr_connection.py --host 192.168.7.205 --port 4001 --client-id 160 --timeout 15"
```

### Run Bot (5 minutes)
```bash
ssh -i ~/.ssh/id_rsa saladbar751@192.168.7.117 "cd ~/ibkr-options-bot && source ~/.venv/bin/activate && timeout 300 python -m src.bot.app"
```

### View Real-Time Logs
```bash
ssh -i ~/.ssh/id_rsa saladbar751@192.168.7.117 "tail -f ~/ibkr-options-bot/logs/bot.log"
```

### Check Git Status
```bash
ssh -i ~/.ssh/id_rsa saladbar751@192.168.7.117 "cd ~/ibkr-options-bot && git status --short"
```

### Update Client ID (if needed)
```bash
ssh -i ~/.ssh/id_rsa saladbar751@192.168.7.117 "cd ~/ibkr-options-bot && sed -i 's/client_id: 101/client_id: 105/' configs/settings.yaml"
```

---

## 📊 Success Metrics

### Immediate (First 15 min)
- ✅ Error 10089 resolved
- ✅ Real-time data flowing
- ✅ Options chain populated
- ✅ Bot runs without crashes

### Short-term (First Hour)
- ✅ Strategy signals generated
- ✅ Bracket orders created (dry_run)
- ✅ No connection drops
- ✅ Logs show clean cycles

### Session Goals
- ✅ 1+ hour stability test passed
- ✅ All safety guards validated
- ✅ Documentation complete
- ✅ Code committed and pushed
- ✅ Production-ready for live deployment decision

---

## 🎓 Key Learnings to Remember

1. **Paper accounts cannot access market data subscriptions** → Use live with `dry_run=true`
2. **API acknowledgement required** → Check portal after subscription purchase
3. **Propagation takes 15-30 minutes** → Be patient after acknowledgement submission
4. **Client IDs persist for ~60 seconds** → Increment for rapid testing
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
