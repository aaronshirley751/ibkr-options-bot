# Phase 3: Live Monitoring Guide & Checklist
**Date:** 2026-01-14
**Status:** 🟢 LIVE EXECUTION (Manual Terminal)
**Strategy:** Option B (TSLA Trend Following)

## 🎯 Objective
Validate the bot's stability and logic in a live trading environment over an extended period (1+ hours).

## 📊 Dashboard
- **Symbol:** TSLA
- **Interval:** 15 Seconds
- **Mode:** Live (Real Money/Paper Account)
- **Strategy:** Whale Entry + Dynamic EMA-20 TRailling Exit

## 🔍 What to Watch For

### 1. Stability (The "Pulse")
*   **Good:** You see this log every ~15 seconds:
    ```
    Cycle complete: 1 symbols in 0.XXs
    ```
*   **Bad:**
    *   "Broker disconnected" / "Client network connection lost"
    *   "Insufficient bars" (Repeatedly)
    *   Process simply stops printing (Hang)

### 2. The Entry (The "Hunt")
Because this is a trend-following strategy, it may scan for hours without entering. This is **normal**.
*   **Scanning:** `Cycle decision ... action='HOLD'`
*   **Trigger:**
    ```
    Cycle decision ... action='BUY_CALL' (or BUY_PUT)
    Placing order ...
    ```
*   **Confirmation:** Look for a new row appearing in `logs/trades.csv`.

### 3. Position Management (The "Ride")
*   Once a position is open, the log changes.
*   **Old Logic:** Checked for fixed take-profits.
*   **New Logic (Option B):**
    ```
    Managing existing position - Checking trends...
    [DEBUG] Checking TSLA price (XXX.XX) vs EMA-20 (XXX.XX)...
    ```
    *   **Hold Condition:** Price > EMA-20 (for Calls)
    *   **Exit Condition:** Price < EMA-20 (Exits position) or Stop Loss (-5%) hit.

## 📝 Actions
*   [ ] **Keep Terminal Open:** Do not close the window where the bot is running.
*   [ ] **Check Trades:** Occasionally check `logs/trades.csv`.
*   [ ] **Stop Command:** To stop the bot safely, press `Ctrl+C` in the terminal **once**. It will finish the current cycle and exit.

## 🚨 Emergency Procedures
If you see runaway orders or a loop:
1.  **Ctrl+C** in the terminal immediately.
2.  Open **IBKR TWS / Mobile App** and manually close positions if needed.
