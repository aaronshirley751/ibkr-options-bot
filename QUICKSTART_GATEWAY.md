# Quick Start: Gateway Setup Checklist

**Your Setup**: Windows PC → serves → Raspberry Pi Bot

---

## ⚡ Quick Actions (30 minutes)

### 1️⃣ Find Your Windows IP
```cmd
ipconfig
```
Look for: `IPv4 Address. . . . . . . . . . . : 192.168.7.XXX`  
**Write it down**: _________________

---

### 2️⃣ Download & Install
- Download: https://www.interactivebrokers.com/en/trading/ibgateway-stable.php
- Run: `ibgateway-stable-standalone-windows-latest.exe`
- Install to default location

---

### 3️⃣ Configure Gateway (CRITICAL STEPS)

**Login**:
- Mode: **"IB API"** (not TWS)
- Trading: **"Paper Trading"**
- Use your IBKR paper account credentials

**Settings** (File → Global Configuration → API → Settings):
- ☑ **Enable ActiveX and Socket Clients** ← MUST CHECK
- Socket port: **4002**
- ☐ Read-Only API ← MUST UNCHECK (bot needs to place orders)
- Trusted IPs: Add **192.168.7.117** (your Pi)

**Restart Gateway** after changing settings

---

### 4️⃣ Verify Port Open
```cmd
netstat -an | findstr "4002"
```
Should show: `TCP    0.0.0.0:4002 ... LISTENING`

---

### 5️⃣ Update Pi Config
```bash
ssh saladbar751@192.168.7.117
cd ~/ibkr-options-bot
nano .env
```

Change line:
```bash
IBKR_HOST=192.168.7.XXX  # Your Windows IP from Step 1
```

Save: `Ctrl+X` → `Y` → `Enter`

---

### 6️⃣ Test from Pi
```bash
cd ~/ibkr-options-bot
source .venv/bin/activate
python test_ibkr_connection.py --host 192.168.7.XXX --port 4002
```

**Must see**: ✓ Connected, ✓ SPY Quote received

---

### 7️⃣ Start Bot
```bash
python -m src.bot.app
```

**Watch for**:
- ✓ "Dry run mode enabled"
- ✓ "Connected to IBKR"
- ✓ First cycle completes

Monitor logs: `tail -f logs/bot.log`

---

## 🚨 Common Issues

| Problem | Solution |
|---------|----------|
| Connection refused | Check Gateway is running, port 4002 listening |
| "Read-Only API" error | Uncheck Read-Only in Gateway settings, restart |
| Firewall blocking | Add port 4002 inbound rule in Windows Firewall |
| Pi can't connect | Add 192.168.7.117 to Gateway Trusted IPs |

---

**After Setup**: Let bot run 2-3 cycles, verify dry_run logging works correctly.

See **GATEWAY_SETUP_WINDOWS.md** for detailed instructions.
