# IB Gateway Setup on Windows (Local Host)

**Date**: December 30, 2025  
**Purpose**: Install IB Gateway on this Windows machine to serve the Raspberry Pi bot

---

## 🎯 Overview

This Windows machine will run IB Gateway and accept API connections from the Raspberry Pi over your local network:

```
┌─────────────────┐         LAN          ┌──────────────────────┐
│  Raspberry Pi   │────────TCP:4002─────►│  This Windows PC     │
│  192.168.7.117  │                      │  (your local IP)     │
│  Bot running    │                      │  IB Gateway running  │
└─────────────────┘                      └──────────────────────┘
```

---

## Step 1: Find Your Windows Machine's Local IP

Open **Command Prompt** or **PowerShell** and run:

```cmd
ipconfig
```

Look for **"Ethernet adapter"** or **"Wireless LAN adapter"** section:
```
Ethernet adapter Ethernet:
   IPv4 Address. . . . . . . . . . . : 192.168.7.XXX
```

**Write down this IP address** - you'll need it for the Pi configuration.

---

## Step 2: Download IB Gateway

1. Visit: https://www.interactivebrokers.com/en/trading/ibgateway-stable.php
2. Click **"Download IB Gateway Standalone"** (Windows)
3. Download: `ibgateway-stable-standalone-windows-latest.exe` (~200 MB)

---

## Step 3: Install IB Gateway

1. Run the downloaded `.exe` installer
2. Accept license agreement
3. Choose installation directory (default is fine: `C:\Jts\ibgateway`)
4. Complete installation
5. Launch **IB Gateway** from Start Menu

---

## Step 4: Initial Login & Configuration

### First Login
1. **Trading Mode**: Select **"IB API"** (not "TWS")
2. **Login Credentials**: Enter your IBKR paper account username/password
3. **Trading Mode**: Select **"Paper Trading"** (not "Live")
4. Click **"Login"**

### Configure API Settings (CRITICAL)

1. After login, go to: **File → Global Configuration → API → Settings**

2. **Enable API**:
   - ☑ **Enable ActiveX and Socket Clients** ✓ (must be checked)

3. **Port Configuration**:
   - **Socket port**: `4002` (paper trading)
   - Leave **"Read-Only API"** UNCHECKED (bot needs to place orders)

4. **Trusted IPs** (Important for Pi access):
   - Click **"+"** to add IP
   - Add: `192.168.7.117` (your Pi's IP)
   - **OR** add: `192.168.7.0/24` (entire subnet - easier if Pi IP changes)
   - **OR** check **"Allow connections from localhost only"** OFF (allows all local network)

5. **Auto-Restart**:
   - ☑ **Auto restart** (recommended - keeps Gateway running if it closes)
   - Time: `03:00` (restarts at 3 AM daily)

6. Click **"OK"** to save settings

7. **Restart IB Gateway** for settings to take effect

---

## Step 5: Verify Gateway is Running

### Check Port is Listening

Open **Command Prompt** and run:

```cmd
netstat -an | findstr "4002"
```

You should see:
```
TCP    0.0.0.0:4002           0.0.0.0:0              LISTENING
```

This confirms Gateway is accepting connections on port 4002.

### Check Windows Firewall (If Needed)

If the Pi cannot connect later, you may need to allow port 4002:

1. Open **Windows Defender Firewall** → **Advanced Settings**
2. Click **"Inbound Rules"** → **"New Rule"**
3. Rule Type: **Port**
4. Protocol: **TCP**, Port: **4002**
5. Action: **Allow the connection**
6. Profile: Check **Private** (for home network)
7. Name: `IBKR Gateway API (port 4002)`

---

## Step 6: Update Raspberry Pi Configuration

SSH into your Pi:

```bash
ssh saladbar751@192.168.7.117
cd ~/ibkr-options-bot
nano .env
```

Update the `IBKR_HOST` line with **your Windows machine's IP**:

```bash
# Before:
IBKR_HOST=127.0.0.1

# After (replace XXX with your actual IP):
IBKR_HOST=192.168.7.XXX
```

Save and exit: `Ctrl+X`, then `Y`, then `Enter`

---

## Step 7: Test Connection from Pi

Still on the Pi, run the connectivity test:

```bash
cd ~/ibkr-options-bot
source .venv/bin/activate
python test_ibkr_connection.py --host 192.168.7.XXX --port 4002 --timeout 10
```

**Expected output**:
```
=== IBKR Connection Test ===
Host: 192.168.7.XXX
Port: 4002
Client ID: 999

Attempting connection...
✓ Connected to IBKR Gateway

Testing market data (SPY)...
✓ SPY Quote: bid=XXX.XX ask=XXX.XX last=XXX.XX

✓ ALL TESTS PASSED
```

---

## Step 8: Start the Bot

Once connectivity test passes, start the bot in dry_run mode:

```bash
cd ~/ibkr-options-bot
source .venv/bin/activate
python -m src.bot.app
```

**Watch for**:
- ✓ "Dry run mode enabled" in startup logs
- ✓ "Connected to IBKR" message
- ✓ First cycle completes without errors
- ✓ "Cycle decision" events in logs

Monitor logs:
```bash
tail -f logs/bot.log
```

---

## Troubleshooting

### Error: "Connection refused"
- **Check**: IB Gateway is running on Windows
- **Check**: Port 4002 is listening (`netstat -an | findstr 4002`)
- **Check**: Windows Firewall allows port 4002
- **Check**: Both machines on same network

### Error: "Could not connect"
- **Check**: Pi's `.env` has correct Windows IP address
- **Check**: IB Gateway "Trusted IPs" includes Pi's IP (192.168.7.117)
- **Check**: Gateway API settings: "Enable ActiveX and Socket Clients" is checked

### Error: "Read-Only API" preventing orders
- **Check**: Gateway settings: "Read-Only API" is UNCHECKED
- **Restart**: Gateway after changing this setting

### Gateway crashes or restarts
- **Check**: Auto-restart is enabled in Gateway settings
- **Check**: Gateway logs in `C:\Jts\ibgateway\logs\`
- **Update**: Gateway to latest version if crashes persist

---

## Keeping Gateway Running 24/7

### Option A: Manual Launch (Simple)
- Launch IB Gateway from Start Menu after Windows boots
- Enable "Auto restart" in Gateway settings (restarts daily at 3 AM)

### Option B: Windows Startup (Recommended)
1. Press `Win+R`, type: `shell:startup`
2. Create shortcut to: `C:\Jts\ibgateway\ibgateway.exe`
3. Gateway will auto-start when Windows boots

### Option C: Task Scheduler (Most Robust)
1. Open **Task Scheduler**
2. Create task: "Launch IB Gateway"
3. Trigger: At system startup, delay 30 seconds
4. Action: Start program `C:\Jts\ibgateway\ibgateway.exe`
5. Conditions: Start only if on AC power (optional)

---

## Security Notes

- **Firewall**: Only allow port 4002 from private/local network
- **Credentials**: Never commit `.env` file to git (already in .gitignore)
- **Paper Trading**: Always use port 4002 until thoroughly tested
- **Monitoring**: Use Discord alerts to track bot activity

---

## Next Steps After Gateway Setup

1. ✅ Gateway running on Windows (this machine)
2. ✅ Port 4002 listening and accessible
3. ✅ Pi `.env` updated with Windows IP
4. ✅ Connectivity test passes from Pi
5. ⏳ Start bot in dry_run mode (2-3 days observation)
6. ⏳ Review logs and Discord alerts
7. ⏳ Graduate to live trading (change `dry_run: false` in settings.yaml)

---

**Setup Complete!** 🎉

Your Windows machine is now the Gateway host for your Pi-based trading bot.
