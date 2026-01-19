# Next Session: Tuesday, January 20, 2026 (Post-MLK Holiday)

## Current Status
- **Last Run**: Friday, Jan 16 (0 Trades, Stable Operation).
- **System**: Operational.
- **Strategy**: "Whale" (Trend Following) - **UPDATED (Jan 19)**
    - `WHALE_LOOKBACK_BARS`: Reduced from 120 (20d) to **60 (10d)** to catch shorter-term breakouts.
    - `WHALE_VOLUME_SPIKE_THRESHOLD`: Reduced from 1.5x to **1.2x** to capture more signals.

## Pre-Market Tasks (Completed)
- [x] **Archive Logs**: Moved Jan 15 & Jan 16 logs to `logs/archive/`.
- [x] **Strategy Tuning**: Code parameters updated in `src/bot/strategy/whale_rules.py`.

## Session Startup (Tuesday Morning)
**Target Start Time**: 09:15 EST

1. **Terminal 1 (Gateway)**:
   ```powershell
   cd "C:\Users\tasms\my-new-project\Trading Bot\ibkr-options-bot"
   docker-compose -f docker-compose.gateway-vnexus.yml up
   ```

2. **Terminal 2 (Bot)**:
   ```powershell
   cd "C:\Users\tasms\my-new-project\Trading Bot\ibkr-options-bot"
   .venv\Scripts\activate
   # Verify connection
   python src/bot/check_connection.py
   # Start Bot
   python -m src.bot.app
   ```
