# Step 1: Flash 64-bit Raspberry Pi OS to SD Card

**Goal:** Write the latest 64-bit Raspberry Pi OS (Bookworm) to your fresh SD card using Raspberry Pi Imager on Windows.

**Duration:** ~15-20 minutes (including download)  
**Prerequisites:**
- Windows PC with internet connection
- Raspberry Pi Imager installed (free from https://www.raspberrypi.com/software/)
- SD card reader connected to Windows
- Fresh SD card (minimum 32GB recommended)
- Raspberry Pi hardware (any recent model: Pi 4, Pi 5, etc.)

---

## Step 1.1: Download and Install Raspberry Pi Imager (if needed)

1. Visit https://www.raspberrypi.com/software/
2. Click **Download for Windows**
3. Run the installer (Raspberry_Pi_Imager_x.x.exe)
4. Follow the installation wizard (defaults are fine)
5. Verify installation by launching **Raspberry Pi Imager** from Start menu

---

## Step 1.2: Prepare SD Card Reader

1. **Insert SD card** into your USB SD card reader
2. **Connect reader to Windows PC** via USB port
3. **Verify detection:**
   - Open **File Explorer**
   - Look for your SD card in the left sidebar (usually shows as "Removable disk" or with a label)
   - Note the drive letter (e.g., `D:`, `E:`, etc.) — you'll see it in Imager

---

## Step 1.3: Launch Raspberry Pi Imager and Select OS

1. **Open Raspberry Pi Imager**
2. You'll see three main buttons:
   - **CHOOSE DEVICE** (left)
   - **CHOOSE OS** (middle)
   - **CHOOSE STORAGE** (right)

### Select Device

1. Click **CHOOSE DEVICE** (left button)
2. A dropdown menu appears with options like:
   - Raspberry Pi 5
   - Raspberry Pi 4
   - Raspberry Pi 3
   - etc.
3. **Select your Pi model** (e.g., "Raspberry Pi 4")
4. Click to confirm

---

## Step 1.4: Select 64-Bit Bookworm OS

1. Click **CHOOSE OS** (middle button)
2. You'll see a menu with several options:
   - **Raspberry Pi OS (64-bit)** — ← **SELECT THIS ONE**
   - Raspberry Pi OS (32-bit)
   - Raspberry Pi OS Lite (64-bit)
   - Raspberry Pi OS Lite (32-bit)
   - Other specialty OS options

3. Click on **"Raspberry Pi OS (64-bit)"** (the full desktop version with GUI)

### Why 64-bit?
- Modern Python 3.11+ assumes 64-bit
- Better performance for financial calculations
- Aligns with server-grade Raspberry Pi deployments

### Why full OS, not Lite?
- Includes SSH, development tools, and package manager
- Lite is headless-only; full gives you flexibility during setup

---

## Step 1.5: Select Storage (Your SD Card)

1. Click **CHOOSE STORAGE** (right button)
2. A list of attached drives appears:
   - Local disks (C:, D:, etc.)
   - USB devices
   - **Your SD card** — typically labeled as "Removable Disk [size]GB" or "SD Card"

3. **CAREFULLY SELECT ONLY YOUR SD CARD**
   - ⚠️ **WARNING:** Selecting the wrong drive will wipe that disk. Verify the size matches your SD card.
   - If unsure, unplug other USB devices first

4. Click to confirm your SD card selection

---

## Step 1.6: Advanced Options (Optional but Recommended)

Before writing, you can set up SSH and user credentials in advance:

1. After selecting storage, you'll see a **"Next"** button at the bottom right
2. Click **Next**
3. A dialog may ask: **"Would you like to apply customization settings?"**
4. Click **"EDIT SETTINGS"** (or skip this if you prefer to do it after first boot)

### If Editing Settings:

**General Tab:**
- **Hostname:** `ibkr-pi` (or your preferred name)
- **Username:** `pi` (default, can keep)
- **Password:** [Set a strong password — you'll SSH with this]
- **Wireless LAN:** [Enter your WiFi SSID and password if using WiFi]
- **Wireless LAN country code:** `US`
- **Timezone:** `America/New_York` (required for correct market hours)
- **Keyboard layout:** `us`

**Services Tab:**
- ✅ **Enable SSH** — Check this box (critical for remote access)
- SSH using password authentication — OK for private network

**Options Tab:**
- Set automatic updates if desired (optional)

**Screenshot of typical settings:**
```
Hostname: ibkr-pi
Username: pi
Password: [your-password]
Enable SSH: ✓ (IMPORTANT)
Timezone: America/New_York
```

5. Click **"SAVE"** to apply settings

---

## Step 1.7: Write the OS to SD Card

1. You're back at the main Imager window
2. Click **"NEXT"** at bottom right (or **"WRITE"** if visible)
3. **Final confirmation dialog** appears:
   ```
   Are you sure you want to continue? 
   All data on [Your SD Card] will be erased.
   ```
4. Click **"YES, CONTINUE"** (double-check you selected the right drive!)

### Writing Progress

The Imager window shows:
- Progress bar filling up
- Estimated time remaining
- Status messages: "Writing...", "Verifying...", "Done!"

**This typically takes 3-8 minutes depending on SD card speed.**

### Completion

- When done, you'll see: **"Write Successful"**
- A green checkmark appears
- Message: "OS successfully written to storage"

---

## Step 1.8: Eject SD Card Safely

1. **In File Explorer**, right-click on the SD card drive
2. Select **"Eject"** (or "Safely Remove Hardware")
3. Wait for the confirmation message
4. **Physically remove the SD card** from the reader
5. Remove the USB reader from your Windows PC

---

## Step 1.9: Verify the Image (Optional)

To confirm the write was successful without booting yet:

1. **Re-insert the SD card** into the reader
2. Open **File Explorer**
3. You should see a partition named **"bootfs"** (or "boot")
4. This contains files like:
   - `bcm2711-rpi-4-b.dtb`
   - `kernel8.img`
   - `config.txt`
   - etc.

If you see these files, the write was successful. ✅

5. **Eject the SD card again** (ready for Pi insertion)

---

## What's Next: Step 2

Once flashed:
1. **Insert SD card into your Raspberry Pi**
2. **Connect power and ethernet (if available)** or WiFi
3. **Power on the Pi**
4. Proceed to **Step 2: Insert SD Card and Boot Pi**

---

## Troubleshooting Step 1

### Issue: Imager shows "No storage detected"
- **Solution:** Unplug SD card reader, wait 5 seconds, plug back in, restart Imager

### Issue: "Permission denied" or "Cannot write to storage"
- **Solution:** Ensure SD card isn't write-protected (small physical switch on reader)
- Try a different USB port

### Issue: Write takes >15 minutes or hangs
- **Solution:** SD card may be faulty; try a different card if available

### Issue: File Explorer doesn't show SD card after flashing
- **Solution:** Restart File Explorer (Ctrl+Shift+Esc, restart explorer.exe) or restart Windows

---

## Summary: Step 1 Checklist

- [ ] Raspberry Pi Imager installed on Windows
- [ ] SD card inserted into reader
- [ ] Reader connected to Windows PC
- [ ] Device selected in Imager (Pi 4 / Pi 5 / etc.)
- [ ] OS selected: **Raspberry Pi OS (64-bit)**
- [ ] Storage selected: **Your SD card** (verified size)
- [ ] Optional: Advanced settings applied (hostname, SSH, timezone)
- [ ] OS written successfully (green checkmark)
- [ ] SD card ejected safely and removed from reader
- [ ] SD card ready for Pi insertion

---

## Estimated Time Remaining

After completing Step 1:
- **Step 2 (Boot Pi):** 5 minutes
- **Step 3 (SSH config):** 10 minutes
- **Step 4 (Python install):** 10 minutes
- **Step 5-6 (Repo + dependencies):** 15 minutes

**Total to get to Step 7 (bot ready):** ~50 minutes

---

✅ **Ready to proceed?** Let me know when Step 1 is complete, and we'll move to Step 2.
