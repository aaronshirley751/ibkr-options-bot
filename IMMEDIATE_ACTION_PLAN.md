# IMMEDIATE ACTION PLAN: Deploy New Code and Test
**Priority**: CRITICAL  
**Timeline**: 15-30 minutes  
**Owner**: User  
**Status**: Ready to execute

---

## The Problem (In 30 Seconds)

The code fixes were written and committed ✅, but the running bot process is still using the OLD code ❌. 

**Evidence**: 
- New code has retry messages like `[historical_retry_sleep]` 
- Bot log has NO such messages
- Bot still taking 60 seconds for historical requests
- Bot returning 0 bars instead of 60 bars

**Solution**: Kill the bot process and restart it

---

## Step 1: Kill Running Bot (2 minutes)

### Option A: Using PowerShell
```powershell
# Find the Python process running the bot
Get-Process python | Where-Object {$_.ProcessName -eq "python"} | Stop-Process -Force

# Verify it's stopped
Get-Process python -ErrorAction SilentlyContinue
```

### Option B: Using Task Manager
1. Press `Ctrl+Shift+Esc` to open Task Manager
2. Find "python.exe" in the list
3. Right-click and select "End Task"
4. Verify no python.exe processes remain

### Option C: Using Command Prompt
```cmd
taskkill /IM python.exe /F
tasklist | findstr python
```

---

## Step 2: Start New Bot Process (2 minutes)

### In PowerShell (Recommended)

```powershell
# Navigate to project
cd "c:\Users\tasms\my-new-project\Trading Bot\ibkr-options-bot"

# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Start bot in background
Start-Process -NoNewWindow -FilePath "$env:PYTHON" -ArgumentList "-m src.bot.app"

# Wait 5 seconds for startup
Start-Sleep -Seconds 5

# Verify it's running
Get-Process python
```

### In Command Prompt
```cmd
cd "c:\Users\tasms\my-new-project\Trading Bot\ibkr-options-bot"

.venv\Scripts\activate.bat

python -m src.bot.app &
```

---

## Step 3: Monitor Logs for Key Signals (5-10 minutes)

### Open a NEW terminal/PowerShell window

```powershell
# Navigate to project
cd "c:\Users\tasms\my-new-project\Trading Bot\ibkr-options-bot"

# Watch logs in real-time
Get-Content logs/bot.log -Wait | Select-String -Pattern "\[HIST\]|historical_|Cycle complete"
```

### Or use tail command (Git Bash or WSL)
```bash
cd /c/Users/tasms/my-new-project/Trading\ Bot/ibkr-options-bot
tail -f logs/bot.log | grep -E "\[HIST\]|historical_|Cycle complete"
```

---

## Step 4: What to Look For

### SUCCESS INDICATORS ✅

**Fix #1 Working** (Asyncio timeout wrapper):
```
[HIST] Requesting: symbol=SPY, duration=3600 S, timeout=120s
[HIST] Completed: symbol=SPY, elapsed=0.5s, bars=61
```
- Elapsed time should be <2 seconds (not 60+)
- Bars should be 60+ (not 0)

**Fix #2 Working** (Exponential backoff retry):
```
Requesting historical data: symbol=SPY, timeout=120
[historical_retry_sleep] Historical data retry: waiting 5s before attempt 2
[historical_retry_sleep] Historical data retry: waiting 15s before attempt 3
```
- Only appears if first attempt fails
- Shows delays of 5 and 15 seconds

**Fix #4 Working** (Updated settings):
```
Requesting historical data: symbol=SPY, duration=3600 S, use_rth=True, timeout=120
```
- Duration should show "3600 S" (not "7200 S")
- use_rth should show "True" (not "False")

### PARTIAL SUCCESS ⚠️ (Subscription Issue - Fix #3)

```
[HIST] Requesting: symbol=SPY, duration=3600 S, timeout=120s
[historical_retry_sleep] Historical data retry: waiting 5s before attempt 2
[historical_retry_sleep] Historical data retry: waiting 15s before attempt 3
[historical_fetch_failed_exhausted] Historical data fetch failed after 3 attempts
Cycle complete: 1 symbols in 35.2s
```

This means:
- ✅ Fixes #1 and #2 are working (retries happening, not timing out)
- ❌ Fix #3 needed (user must verify IBKR subscription status)
- Action: See "If Subscription Issue" section below

### FAILURE INDICATORS ❌

**Fix #1 NOT Working**:
```
[HIST] Requesting: symbol=SPY, duration=3600 S, timeout=120s
[HIST] Completed: symbol=SPY, elapsed=60.01s, bars=0
```
- Still taking 60 seconds
- Means bot process is still running OLD code
- Kill process again and restart

---

## Step 5: What Happens Next

### If SUCCESS (60+ bars retrieved in <2 seconds)

You're ready for **Connectivity & Stability Testing**:

```bash
# 1. Run IBKR connection test
make ibkr-test

# 2. Monitor bot for 30 minutes
# Watch for consistent cycle completion
# Look for cycle times in 5-15 second range

# 3. Check for errors
tail -100 logs/bot.log | grep -i error
```

### If PARTIAL SUCCESS (Retries happening but 0 bars)

You need **Fix #3: IBKR Account Subscription Verification**

**User Action** (1-2 hours):

1. Log into IBKR web portal: https://www.interactivebrokers.com
2. Navigate: **Account** → **Subscriptions** → **Market Data Subscriptions**
3. Look for **US Stocks and Options (SPY)**
4. Check status:
   - ✅ "Active" = Subscription is good, try bot restart again
   - ⚠️ "Trial" = Expires soon, renew to maintain
   - ❌ "Expired" = Need to renew
   - ❌ Missing = Need to subscribe

5. If subscription is inactive:
   - Subscribe or activate the "US Stocks 25min Delay" (free)
   - Or use your existing subscription package

6. Wait 5 minutes for subscription to be processed

7. Kill and restart bot again:
   ```bash
   # Kill
   taskkill /IM python.exe /F
   sleep 10
   
   # Restart
   python -m src.bot.app &
   ```

8. Monitor logs - should now see 60+ bars in <2 seconds

### If FAILURE (Still 60 seconds, 0 bars, no retries)

The old code is still running. This shouldn't happen if you followed Step 1-2 correctly:

```bash
# Verify the process is actually killed
tasklist | findstr python    # Should be EMPTY

# If python.exe still showing:
taskkill /IM python.exe /F /T

# Wait and check again
tasklist | findstr python    # Should be EMPTY now

# Then restart using Step 2
```

---

## Step 6: Validate All Fixes

Once you have 60+ bars being retrieved in <2 seconds:

### Verify Fix #1 (Asyncio timeout)
```bash
grep "\[historical_timeout_asyncio\]" logs/bot.log
```
- Should be EMPTY if no timeouts occur (normal)
- If errors happen later, should capture them gracefully

### Verify Fix #2 (Exponential backoff)
```bash
grep "historical_retry_sleep" logs/bot.log
```
- Should be EMPTY in normal operation (no failures)
- If failures occur, should show [0s, 5s, 15s] delays
- Should show [historical_fetch_failed_exhausted] after 3 attempts

### Verify Fix #4 (Settings)
```bash
grep "duration=3600\|use_rth=True\|timeout=" logs/bot.log | head -5
```
- Should show: `duration=3600 S, use_rth=True, timeout=120`

---

## Quick Reference: Commands to Know

| Purpose | Command |
|---------|---------|
| Kill bot | `taskkill /IM python.exe /F` |
| Start bot | `python -m src.bot.app &` |
| Watch logs | `tail -f logs/bot.log \| grep -E "\[HIST\]\|historical_"` |
| Check for success | `grep "elapsed=.*bars=[6-9]" logs/bot.log` |
| Check for retries | `grep "historical_retry_sleep" logs/bot.log` |
| Check for failures | `grep "historical_fetch_failed_exhausted" logs/bot.log` |
| Latest cycles | `tail -20 logs/bot.log \| grep "Cycle complete"` |

---

## Expected Timeline

| Time | Event | Action |
|------|-------|--------|
| T+0 | Kill old bot | Step 1 |
| T+1 | Start new bot | Step 2 |
| T+2-5 | Wait for startup | Check if process running |
| T+5-15 | First cycles running | Monitor logs (Step 3-4) |
| T+15-30 | Pattern clear | Identify success/failure |
| T+30+ | If success: Continue to testing | If failure: Debug process restart |

---

## Troubleshooting

### "Process not found" errors
```bash
# This is normal - means bot isn't running
# Just proceed with starting it in Step 2
```

### Can't activate venv
```bash
# Re-create venv if needed:
python -m venv .venv
.venv\Scripts\activate.bat
pip install -r requirements.txt -r requirements-dev.txt
```

### Bot starts but no logs appear
```bash
# Check if bot is actually running:
tasklist | findstr python  # Should show python.exe

# Check log file exists:
ls logs/bot.log

# Check for errors:
python -m src.bot.app  # Run directly to see errors
```

### Still seeing 60-second timeouts
This means:
1. ❌ Bot process wasn't fully killed before restart
2. Or: ❌ Old process restarted automatically
3. Or: ❌ Multiple bot processes running

Solution:
```bash
# Kill ALL python processes
taskkill /IM python.exe /F /T

# Verify empty
tasklist | findstr python  # Should be empty

# Wait 10 seconds
# Then restart bot
```

---

## Document Info
**Created**: 2026-01-12 13:15 UTC  
**For**: Production Deployment  
**Next**: See [LOG_ANALYSIS_AND_FINDINGS_2026_01_12.md](LOG_ANALYSIS_AND_FINDINGS_2026_01_12.md) for technical details
