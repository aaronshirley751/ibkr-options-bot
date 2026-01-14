# Round 4 Session Guide: January 15, 2026

## 🎯 Objective
**Full Trading Day Execution.**
The system is now stability-tested and bug-free. The goal for this session is to run the bot unsupervised (or lightly supervised) for the entire trading day (09:30 - 16:00 EST).

---

## 🚀 Startup Instructions (09:15 AM EST)

### 1. Launch the Environment
Open your Git Bash or Terminal in VS Code.

### 2. Start the Bot (Manual Mode)
Use the manual command to ensure no sandbox timeouts occur:
```bash
.venv/Scripts/python -m src.bot.app
```
*Note: Do not close this terminal window.*

### 3. Verify Startup
Check the logs to confirm connection and data flow:
```bash
tail -f logs/bot.log
```
**Look for:**
- `Connected to IBKR`
- `Market Data Connection: Active`
- `Cycle complete: 1 symbols` (appearing every ~15s)

---

## 📊 Strategy Configuration (Current)
*   **Symbol**: `TSLA`
*   **Strategy**: Option B (Whale / Trend Follow)
*   **Risk**: 80% Equity per trade
*   **Exit**: Dynamic (1-Hour EMA20 Breakdown) or Hard Stop (-5%)

**Optional Adjustments:**
If you wish to add `NVDA` or `AMD`, edit `configs/settings.yaml` **before** starting the bot:
```yaml
symbols:
  - "TSLA"
  - "NVDA"
```

---

## 🛑 Shutdown
To stop the bot at the end of the day (16:00 EST):
1.  Click inside the terminal running the bot.
2.  Press `Ctrl + C`.
3.  Wait for the `Shutdown signal received` message.

---

## 🔗 Reference Docs
*   [Yesterday's Report](FINAL_SESSION_REPORT_2026_01_14.md)
*   [Troubleshooting Logs](logs/bot.log)
