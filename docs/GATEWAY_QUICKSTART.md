# Gateway Quick Start for Pi

## Option 1: GHCR Authentication (Recommended)

### 1. Create GitHub Personal Access Token

- Go to: https://github.com/settings/tokens
- Generate new token (classic)
- Select scope: `read:packages`
- Copy the token

### 2. Authenticate on Pi

```bash
ssh pi@<your-pi-ip>
echo "YOUR_TOKEN_HERE" | docker login ghcr.io -u YOUR_GITHUB_USERNAME --password-stdin
```

### 3. Start Gateway

```bash
cd ~/ibkr-options-bot
cp docker-compose.gateway.yml.backup docker-compose.gateway.yml  # Restore original
make gateway-up
```

### 4. Verify

```bash
docker ps  # Should show ibkr-gateway running
make ibkr-test  # Should connect and fetch quotes
```

---

## Option 2: VNC Gateway (If GHCR fails)

### 1. Use VNC-based image

```bash
cp docker-compose.gateway-vnexus.yml docker-compose.gateway.yml
make gateway-up
```

### 2. Connect via VNC to complete 2FA if required

```bash
# From your desktop:
vncviewer <pi-ip>:5900
# Password: vncpassword
```

---

## Option 3: Manual Installation (Last Resort)

### 1. Download IB Gateway from IBKR website
### 2. Install on Pi directly
### 3. Configure API settings manually
### 4. Update .env with correct port

---

## Verification Checklist

- [ ] Gateway container running: `docker ps | grep gateway`
- [ ] Port 4002 accessible: `nc -zv localhost 4002`
- [ ] API responds: `make ibkr-test`
- [ ] Market data works: Check test output for stock quotes

---

## Troubleshooting

### Gateway won't start
- Check Docker is running: `systemctl status docker`
- Check logs: `docker-compose logs gateway`
- Verify credentials in `.env` file

### Authentication fails
- Ensure GitHub token has `read:packages` scope
- Try re-authenticating: `docker logout ghcr.io && docker login ghcr.io`
- Check token hasn't expired

### Port not accessible
- Check firewall: `sudo ufw status`
- Verify port in docker-compose.yaml matches settings.yaml
- Try different Gateway image (VNC version)

### 2FA required
- Use VNC Gateway option
- Connect via VNC viewer to complete authentication
- Or disable 2FA in IBKR account settings (not recommended for live accounts)

---

## Next Steps After Gateway Validation

1. Run pre-deployment validation: `bash scripts/validate_deployment.sh`
2. Start bot in dry_run mode: `python -m src.bot.app`
3. Monitor logs: `tail -f logs/bot.log`
4. Verify no order execution (dry_run=true)
5. Test Discord webhook alerts (if configured)
