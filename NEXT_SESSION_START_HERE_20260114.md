# Start Here Next - January 14, 2026

**Current State**: LIVE READY (Configured for IWM, ATM, Real Money)

## 1. Startup Procedure (09:15 ET)
Since the bot is already configured for production, you just need to launch it.

1. **Open Workspace**: `c:\Users\tasms\my-new-project\Trading Bot\ibkr-options-bot`
2. **Launch Gateway**: Ensure IBKR Gateway is running and healthy.
3. **Start Bot**:
   ```bash
   .venv/Scripts/python -m src.bot.app
   ```
   *Note: Ensure you do NOT have multiple instances running.*

## 2. Validation Checklist (First 5 Minutes)
Watch the terminal logs for these confirmations:
- [ ] `✓ Gateway connected successfully`
- [ ] `✓ Symbols configured: ['IWM']`
- [ ] `dry_run is FALSE` (Warning message)
- [ ] `Historical data success` (Data streaming)

## 3. What to Expect
- **Morning Volatility**: The bot will likely process signals starting at 09:30.
- **First Trade**: When a valid Scalp or Whale signal triggers:
    - Log: `[ORDER] BUY IWM ...`
    - Check Interactive Brokers mobile app/TWS to confirm execution.
    - Bot will automatically place Bracket Orders (Profit Taker / Stop Loss).

## 4. Emergency Controls
If the bot behaves unexpectedly:
1. **Kill Switch**: `Ctrl+C` in the terminal.
2. **Liquidate**: Manually close positions in TWS/Mobile App.
3. **Logs**: Check `logs/bot.log` for errors.

## Critical Settings Recap
- **Risk**: 50% Account Usage per trade.
- **Loss Limit**: Stops trading if -15% daily equity drop.
- **Asset**: IWM Calls/Puts (ATM).

---
**Prepared By**: GitHub Copilot
**Date**: 2026-01-13
