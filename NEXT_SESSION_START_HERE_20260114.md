# 🚀 START HERE - Next Session Quick Start Guide (2026-01-14)

## 🚨 STRATEGY PIVOT: TSLA Dynamic Trend Following
**Last Updated:** 2026-01-13 (End of Strategy Session)

We have pivoted from a generic SPY/IWM scalp strategy to a **High-Volatility Trend Following** strategy on **TSLA**, specifically optimized for a small account (~$523).

### Key Strategy Changes (Option B)
- **Asset:** `TSLA` (Tesla) ONLY.
- **Entry:** "Whale Entry" (Volume spikes + Price movement).
- **Exit (Dynamic):** Closes position if **Hourly Price < EMA-20**.
- **Risk:**
  - **No Take Profit:** We let winners run (up to +200% in backtests).
  - **Stop Loss:** 5% Hard Stop (Survival mode).
  - **Daily Loss Limit:** 10%.
- **Logic:** `scheduler.py` has been patched to include a "Dynamic Position Management" block that checks the 1-hour chart against the EMA-20 every cycle.

### 📋 Checklist for Next Session
1. **Verify Live Connection:** ✅ **VERIFIED**
   Connected to 192.168.7.205:4001.

2. **Check Configuration:** ✅ **VERIFIED**
   - `symbols`: `["TSLA"]`
   - `max_risk_pct_per_trade`: `0.80`
   - `take_profit_pct`: `null` (Fixed code to allow this)
   - `stop_loss_pct`: `0.05`
   - `dry_run`: `true`

3. **Dry Run (IN PROGRESS):**
   The bot logic and data fetching have been verified. Run the bot now and leave it running for the session to validate the EMA logic during RTH.
   ```bash
   python -m src.bot.app
   ```
   *Plan: Validate 1-Hour EMA calculations -> Stop Bot -> Switch to Live -> Restart.*

4. **Monitor Logs:**
   Watch for the new log line:
   `"[DYNAMIC EXIT] Checking TSLA price ... vs EMA-20 ..."`
   *(Note: This logic only triggers when you have an open position. Since we are starting fresh, look for "Cycle decision" logs first.)*

### ⚠️ Important Notes
- **Account Sizing:** The strategy uses 80% risk per trade. This is intentional for the "Home Run" growth phase.
- **Drawdowns:** Expect high volatility. The bot creates few signals but aims for large trend capture.
- **Disabled Scalp:** The `scalp_signal` function is now overridden to return "HOLD" in `scheduler.py` to prevent noise.

### 📂 Key Files Modified
- `src/bot/scheduler.py`: Added EMA-20 Dynamic Exit Logic.
- `configs/settings.yaml`: Updated for TSLA & Dynamic Risk.
- `README.md`: Updated to reflect strategy pivot.

---
**Next Session Goal:** Live Dry-Run verification of the 1-Hour EMA calculation and order execution flow during market hours.
