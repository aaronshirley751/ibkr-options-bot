# Round 5 Session Guide: January 16, 2026

## 🎯 Objective
**Continuous Full-Day Operation.**
Building on the success of Jan 15, the goal for today is to achieve a completely uninterrupted run from 09:15 to 16:05 EST. We want to eliminate the morning restarts observed on Jan 15.

---

## 🚀 Startup Instructions (09:15 AM EST)

### 1. Launch the Environment
Open your Git Bash or Terminal in VS Code.

### 2. Start the Bot (Manual Mode)
Use the manual command for maximum stability:
```bash
.venv/Scripts/python -m src.bot.app
```
*Note: Do not close this terminal window.*

### 3. Verify Startup
Check the logs to confirm connection and data flow for ALL 3 symbols:
```bash
tail -f logs/bot.log
```
**Look for:**
- `Connected to IBKR`
- `Cycle complete: 3 symbols` (appearing every ~15s)
- `[HIST] Completed: symbol=TSLA...`
- `[HIST] Completed: symbol=NVDA...`
- `[HIST] Completed: symbol=AMD...`

---

## 📊 Strategy Configuration (Current)
*   **Symbols**: `TSLA`, `NVDA`, `AMD`
*   **Strategy**: Option B (Whale / Trend Follow)
*   **Risk**: 80% Equity per trade
*   **Exit**: Dynamic (1-Hour EMA20 Breakdown) or Hard Stop (-5%)

**Note on Trading Frequency:**
Yesterday saw 0 trades. This is acceptable for the "Whale" strategy. Do not force trades unless you suspect a data issue. If confident the market is moving and no signal fires, check `logs/bot.jsonl` for signal confidence scores.

---

## 🛑 Shutdown
To stop the bot at the end of the day (16:05 EST):
1.  **Ctrl+C** in the terminal running the bot.
2.  Wait for "Graceful shutdown complete" message.
3.  Run the reporting command (to be provided).
