# Round 3 QA Review - Addendum

Based on your clarifications, I'm updating the recommendations with additional critical items and Discord webhook support.

---

## 🚨 CRITICAL BLOCKER: Gateway Validation Required

**Status:** Gateway connectivity has NOT been validated on target Pi hardware.

This is the **#1 deployment blocker**. Without a working Gateway, the bot cannot execute any trading operations. Based on the session logs, you have multiple Gateway options prepared but none confirmed working.

**Copilot Prompt (Pre-Deployment Validation Script):**
```
Create scripts/validate_deployment.sh that performs pre-deployment checks:

#!/bin/bash
set -e

echo "=== IBKR Options Bot Pre-Deployment Validation ==="
echo ""

# Check 1: Python environment
echo "[1/6] Checking Python environment..."
python3 --version || { echo "❌ Python3 not found"; exit 1; }
echo "✓ Python OK"

# Check 2: Dependencies
echo "[2/6] Checking dependencies..."
python3 -c "import pandas; import pydantic; import loguru" || { echo "❌ Missing dependencies"; exit 1; }
echo "✓ Dependencies OK"

# Check 3: Configuration
echo "[3/6] Checking configuration..."
python3 -c "
from src.bot.settings import get_settings
s = get_settings()
assert s.dry_run == True, 'FATAL: dry_run must be True for initial deployment'
print(f'  dry_run: {s.dry_run}')
print(f'  symbols: {s.symbols}')
print(f'  broker.port: {s.broker.port}')
" || { echo "❌ Configuration invalid"; exit 1; }
echo "✓ Configuration OK"

# Check 4: Gateway connectivity
echo "[4/6] Checking Gateway connectivity..."
GATEWAY_HOST="${IBKR_HOST:-127.0.0.1}"
GATEWAY_PORT="${IBKR_PORT:-4002}"
timeout 5 bash -c "</dev/tcp/$GATEWAY_HOST/$GATEWAY_PORT" 2>/dev/null && {
    echo "✓ Gateway port $GATEWAY_PORT is accessible"
} || {
    echo "❌ Gateway not accessible at $GATEWAY_HOST:$GATEWAY_PORT"
    echo "  Run: make gateway-up"
    exit 1
}

# Check 5: IBKR API test
echo "[5/6] Testing IBKR API connection..."
python3 test_ibkr_connection.py --host "$GATEWAY_HOST" --port "$GATEWAY_PORT" --timeout 10 || {
    echo "⚠️  IBKR API test had issues (check output above)"
}

# Check 6: Test suite
echo "[6/6] Running test suite..."
pytest tests/ -q || { echo "❌ Tests failed"; exit 1; }
echo "✓ Tests OK"

echo ""
echo "=== All checks passed! Ready for deployment ==="
```

---

## 🆕 NEW: Discord Webhook Support

Adding Discord webhook support to the monitoring module. Discord webhooks are simpler than Slack (same JSON format) but use a different URL structure.

**Copilot Prompt:**
```
Add Discord webhook support to src/bot/monitoring.py:

1. Add new function notify_discord():

def notify_discord(webhook_url: Optional[str], message: str, username: str = "IBKR Bot") -> None:
    """Send notification to Discord channel via webhook.
    
    Args:
        webhook_url: Discord webhook URL (from channel settings > Integrations > Webhooks)
        message: Message text to send
        username: Bot username to display (default: "IBKR Bot")
    """
    if not webhook_url:
        return
    
    # Discord webhook payload format
    payload = {
        "content": message,
        "username": username,
    }
    
    ok = _http_post(webhook_url, payload)
    if not ok:
        logger.debug("Discord notification failed")


2. Update alert_all() to include Discord:

def alert_all(settings: dict, message: str) -> None:
    """Send alert to all configured notification channels."""
    mon = settings.get("monitoring", {})
    if not mon or mon.get("alerts_enabled") is False:
        return
    
    # Discord (primary)
    notify_discord(mon.get("discord_webhook_url"), message)
    
    # Slack (legacy support)
    notify_slack(mon.get("slack_webhook_url"), message)
    
    # Telegram (legacy support)
    notify_telegram(mon.get("telegram_bot_token"), mon.get("telegram_chat_id"), message)


3. Update src/bot/settings.py MonitoringSettings:

class MonitoringSettings(BaseModel):
    alerts_enabled: bool = Field(default=True)
    heartbeat_url: Optional[str] = Field(default=None)
    discord_webhook_url: Optional[str] = Field(default=None)  # NEW - Primary
    slack_webhook_url: Optional[str] = Field(default=None)
    telegram_bot_token: Optional[str] = Field(default=None)
    telegram_chat_id: Optional[str] = Field(default=None)


4. Update configs/settings.yaml monitoring section:

monitoring:
  alerts_enabled: true
  heartbeat_url: ""
  discord_webhook_url: ""  # Discord: Server Settings > Integrations > Webhooks > Copy URL
  slack_webhook_url: ""    # Optional: Slack Incoming Webhook URL
  telegram_bot_token: ""   # Optional: Telegram bot token
  telegram_chat_id: ""     # Optional: Telegram chat id
```

**Copilot Prompt (Discord Tests):**
```
Add Discord tests to tests/test_monitoring.py:

class TestNotifyDiscord:
    """Test Discord notifications."""

    @mock.patch("src.bot.monitoring._http_post")
    def test_notify_discord_success(self, mock_http_post):
        """Successfully sends Discord message."""
        mock_http_post.return_value = True

        from src.bot.monitoring import notify_discord
        notify_discord("https://discord.com/api/webhooks/123/abc", "Test message")

        mock_http_post.assert_called_once()
        call_args = mock_http_post.call_args
        assert "discord.com" in call_args[0][0]
        assert call_args[0][1]["content"] == "Test message"
        assert call_args[0][1]["username"] == "IBKR Bot"

    @mock.patch("src.bot.monitoring._http_post")
    def test_notify_discord_custom_username(self, mock_http_post):
        """Uses custom username when provided."""
        mock_http_post.return_value = True

        from src.bot.monitoring import notify_discord
        notify_discord("https://discord.com/api/webhooks/123/abc", "Test", username="Trading Bot")

        call_args = mock_http_post.call_args
        assert call_args[0][1]["username"] == "Trading Bot"

    def test_notify_discord_none_webhook(self):
        """Skips if webhook URL is None."""
        from src.bot.monitoring import notify_discord
        notify_discord(None, "Test message")  # Should not raise

    def test_notify_discord_empty_webhook(self):
        """Skips if webhook URL is empty."""
        from src.bot.monitoring import notify_discord
        notify_discord("", "Test message")  # Should not raise

    @mock.patch("src.bot.monitoring._http_post")
    def test_notify_discord_failure_graceful(self, mock_http_post):
        """Handles notification failure gracefully."""
        mock_http_post.return_value = False

        from src.bot.monitoring import notify_discord
        notify_discord("https://discord.com/api/webhooks/123/abc", "Test")  # Should not raise


Also update TestAlertAll to verify Discord is called:

    @mock.patch("src.bot.monitoring.notify_discord")
    @mock.patch("src.bot.monitoring.notify_slack")
    @mock.patch("src.bot.monitoring.notify_telegram")
    def test_alert_all_sends_discord(self, mock_telegram, mock_slack, mock_discord):
        """Sends to Discord when configured."""
        settings = {
            "monitoring": {
                "alerts_enabled": True,
                "discord_webhook_url": "https://discord.com/api/webhooks/123/abc",
            }
        }

        alert_all(settings, "Alert message")

        mock_discord.assert_called_once_with(
            "https://discord.com/api/webhooks/123/abc", 
            "Alert message"
        )
```

---

## 📊 Pi Hardware Guidance: Concurrent Symbols

**Recommendation:** For Raspberry Pi 4 (4GB RAM), start conservative:

| Setting | Recommended | Reason |
|---------|-------------|--------|
| `max_concurrent_symbols` | **1** | Single-threaded processing initially |
| `interval_seconds` | **300** (5 min) | Reduces API load, gives Pi breathing room |
| `symbols` | **["SPY"]** | Single symbol for baseline |

**Copilot Prompt:**
```
Update configs/settings.yaml with conservative Pi-friendly defaults for Phase 1:

# Phase 1 Pi-optimized settings
symbols:
  - "SPY"  # Start with single symbol for baseline

schedule:
  interval_seconds: 300  # 5 minutes - reduces load on Pi
  max_concurrent_symbols: 1  # Single-threaded for Pi stability

# Add comment explaining the rationale
# NOTE: These conservative settings are for Phase 1 Pi deployment.
# After baseline is established, consider:
#   - interval_seconds: 180 (3 min) for faster response
#   - max_concurrent_symbols: 2 for parallel processing
#   - symbols: ["SPY", "QQQ"] for diversification
```

---

## 📋 Updated Priority Matrix

Given your timeline (few days paper trading), here's the revised priority:

### Must Complete Before Deployment (Day 0)

| # | Issue | Time Est. | Impact |
|---|-------|-----------|--------|
| 1 | Fix emulate_oco indentation | 5 min | Runtime crash |
| 2 | Set dry_run: true | 1 min | Safety critical |
| 3 | Fix save_equity_state race condition | 10 min | Data corruption |
| 4 | Add Discord webhook support | 20 min | Your preferred alerting |
| 5 | Validate Gateway on Pi | 30 min | Deployment blocker |
| 6 | Update settings.yaml for Pi | 5 min | Performance |

### Should Complete Day 1-2

| # | Issue | Time Est. | Impact |
|---|-------|-----------|--------|
| 7 | Add max_duration test | 10 min | Test coverage |
| 8 | Add broker connection validation | 15 min | Reliability |
| 9 | Add SIGTERM handler | 10 min | Clean shutdown |
| 10 | Improve error messages | 15 min | Debugging |

### Can Defer Until After Baseline

| # | Issue | Notes |
|---|-------|-------|
| 11 | Health check endpoint | Useful for monitoring but not critical |
| 12 | Retry logic | Can add after observing failure patterns |
| 13 | Position verification in OCO | Enhancement |
| 14 | Shared test fixtures | Code quality |
| 15 | Type hints | Code quality |

---

## Gateway Resolution: Recommended Path

Based on session logs, here's the recommended Gateway resolution sequence:

**Copilot Prompt (Gateway Resolution Guide):**
```
Create docs/GATEWAY_QUICKSTART.md with step-by-step Gateway setup:

# Gateway Quick Start for Pi

## Option 1: GHCR Authentication (Recommended)

1. Create GitHub Personal Access Token:
   - Go to: https://github.com/settings/tokens
   - Generate new token (classic)
   - Select scope: `read:packages`
   - Copy the token

2. Authenticate on Pi:
   ```bash
   ssh pi@<your-pi-ip>
   echo "YOUR_TOKEN_HERE" | docker login ghcr.io -u YOUR_GITHUB_USERNAME --password-stdin
   ```

3. Start Gateway:
   ```bash
   cd ~/ibkr-options-bot
   cp docker-compose.gateway.yml.backup docker-compose.gateway.yml  # Restore original
   make gateway-up
   ```

4. Verify:
   ```bash
   docker ps  # Should show ibkr-gateway running
   make ibkr-test  # Should connect and fetch quotes
   ```

## Option 2: VNC Gateway (If GHCR fails)

1. Use VNC-based image:
   ```bash
   cp docker-compose.gateway-vnexus.yml docker-compose.gateway.yml
   make gateway-up
   ```

2. Connect via VNC to complete 2FA if required:
   ```bash
   # From your desktop:
   vncviewer <pi-ip>:5900
   # Password: vncpassword
   ```

## Option 3: Manual Installation (Last Resort)

1. Download IB Gateway from IBKR website
2. Install on Pi directly
3. Configure API settings manually
4. Update .env with correct port

## Verification Checklist

- [ ] Gateway container running: `docker ps | grep gateway`
- [ ] Port 4002 accessible: `nc -zv localhost 4002`
- [ ] API responds: `make ibkr-test`
- [ ] Market data works: Check test output for stock quotes
```

---

## Consolidated Day 0 Deployment Prompt

Here's a single comprehensive prompt to prepare for deployment:

**Copilot Prompt (Complete Day 0 Preparation):**
```
Prepare the IBKR Options Bot for Phase 1 Pi deployment. Complete these tasks in order:

## Task 1: Fix Critical Code Issues

### 1a. Fix emulate_oco indentation (src/bot/execution.py)
Inside the while True loop in emulate_oco(), ensure all statements are at exactly 12 spaces indentation. The safety check and progress logging comments have extra leading spaces that must be removed.

### 1b. Fix save_equity_state race condition (src/bot/risk.py)
Add unique temp file suffix using os.getpid() and uuid to prevent race conditions:
```python
import uuid
tmp = path.with_suffix(f".tmp.{os.getpid()}.{uuid.uuid4().hex[:8]}")
```

## Task 2: Add Discord Webhook Support

### 2a. Add notify_discord() to src/bot/monitoring.py
Function that sends message via Discord webhook with payload: {"content": message, "username": "IBKR Bot"}

### 2b. Update alert_all() to call notify_discord() first

### 2c. Add discord_webhook_url to MonitoringSettings in src/bot/settings.py

## Task 3: Update Configuration

### 3a. In configs/settings.yaml:
- Set dry_run: true
- Set interval_seconds: 300
- Set max_concurrent_symbols: 1
- Set symbols to only ["SPY"]
- Add discord_webhook_url: "" to monitoring section

## Task 4: Add Discord Tests

### 4a. Add TestNotifyDiscord class to tests/test_monitoring.py with tests for:
- Success case
- Custom username
- None/empty webhook handling
- Failure graceful handling

## Task 5: Create Validation Script

### 5a. Create scripts/validate_deployment.sh that checks:
- Python environment
- Dependencies installed
- Configuration valid (dry_run=true)
- Gateway port accessible
- IBKR API connection
- Test suite passes

## Task 6: Run Verification

After completing all tasks:
1. black src tests
2. ruff check src tests
3. pytest tests/ -v
4. python -c "from src.bot.settings import get_settings; s = get_settings(); assert s.dry_run, 'dry_run must be True'"

Report any failures.
```

---

## Final Pre-Deployment Checklist

```
□ Code Fixes
  □ emulate_oco indentation fixed
  □ save_equity_state race condition fixed
  □ Discord webhook support added
  
□ Configuration
  □ dry_run: true in settings.yaml
  □ Conservative Pi settings applied
  □ Discord webhook URL configured (when ready)
  
□ Gateway
  □ GHCR authentication completed OR alternative image selected
  □ Gateway container starts successfully
  □ Port 4002 accessible
  □ make ibkr-test passes
  
□ Testing
  □ All tests pass (pytest tests/ -v)
  □ Discord tests included
  □ Validation script created and runs clean
  
□ Documentation
  □ Gateway quickstart guide created
  □ Deployment steps documented
```

---

## Questions Resolved

| Question | Answer | Action |
|----------|--------|--------|
| Gateway validated? | No | Added as critical blocker with resolution guide |
| Alert preference? | Discord | Added Discord webhook support |
| Concurrent symbols for Pi? | Unknown | Recommended 1 (conservative) with upgrade path |
| Paper trading duration? | Few days | Prioritized Day 0 items, deferred enhancements |

---

Would you like me to elaborate on any specific item, or shall I provide additional prompts for the Gateway resolution process?