from __future__ import annotations

import json
from typing import Optional
from urllib import request

from .log import logger


def _http_post(
    url: str, payload: dict, headers: Optional[dict] = None, timeout: int = 10
) -> bool:
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("User-Agent", "Mozilla/5.0 (compatible; IBKR-Bot/1.0)")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with request.urlopen(req, timeout=timeout) as resp:  # nosec B310
            code = getattr(resp, "getcode", lambda: 0)()
            return 200 <= code < 300
    except request.HTTPError as e:  # pylint: disable=broad-except
        # Discord webhooks return 204 No Content on success, which urlopen treats as error
        # Check if it's actually a success response
        if e.code in (200, 201, 204):
            logger.debug(f"HTTP POST to {url} succeeded with code {e.code}")
            return True
        logger.debug(f"HTTP POST failed to {url}: HTTP {e.code} - {e.reason}")
        return False
    except Exception as e:  # pylint: disable=broad-except
        logger.debug(f"HTTP POST failed to {url}: {type(e).__name__}: {e}")
        return False


def send_heartbeat(heartbeat_url: Optional[str]) -> None:
    if not heartbeat_url:
        return
    try:
        # For healthchecks.io, a simple GET is typical; support POST too
        req = request.Request(heartbeat_url, method="GET")
        with request.urlopen(req, timeout=5) as resp:  # nosec B310
            _ = getattr(resp, "read", lambda: b"")()
    except Exception as e:  # pylint: disable=broad-except
        logger.debug(f"Heartbeat failed: {e}")


def notify_slack(webhook_url: Optional[str], message: str) -> None:
    if not webhook_url:
        return
    payload = {"text": message}
    ok = _http_post(webhook_url, payload)
    if not ok:
        logger.debug("Slack notification failed")


def notify_telegram(
    bot_token: Optional[str], chat_id: Optional[str], message: str
) -> None:
    if not bot_token or not chat_id:
        return
    # Telegram sendMessage API
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message}
    ok = _http_post(url, payload)
    if not ok:
        logger.debug("Telegram notification failed")


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


def alert_all(settings: dict, message: str) -> None:
    """Send alert to all configured notification channels."""
    mon = settings.get("monitoring", {})
    if not mon or mon.get("alerts_enabled") is False:
        return
    
    # Discord (primary)
    username = mon.get("discord_username")
    if username:
        notify_discord(mon.get("discord_webhook_url"), message, username=username)
    else:
        notify_discord(mon.get("discord_webhook_url"), message)
    
    # Slack (legacy support)
    notify_slack(mon.get("slack_webhook_url"), message)
    
    # Telegram (legacy support)
    notify_telegram(mon.get("telegram_bot_token"), mon.get("telegram_chat_id"), message)


def trade_alert(
    settings: dict,
    stage: str,
    symbol: str,
    action: str,
    quantity: float,
    price: float,
    order_id: Optional[str] = None,
    pnl: Optional[float] = None,
) -> None:
    """Send trade lifecycle alert to Discord and legacy channels.

    Args:
        stage: "Entry" or "Exit" label
        symbol: Underlying or option symbol
        action: BUY/SELL direction
        quantity: Filled or intended quantity
        price: Fill or intended price
        order_id: Optional order identifier (DRYRUN for simulations)
        pnl: Profit/loss placeholder; pass None when unknown
    """
    mon = settings.get("monitoring", {})
    if not mon or mon.get("alerts_enabled") is False:
        return

    username = mon.get("discord_username") or "IBKR Bot"
    pnl_txt = "n/a" if pnl is None else f"{pnl:.2f}"
    oid_txt = f" ({order_id})" if order_id else ""
    msg = (
        f"{stage}: {action} {quantity} {symbol} @ {price:.2f}{oid_txt} | P/L: {pnl_txt}"
    )

    notify_discord(mon.get("discord_webhook_url"), msg, username=username)
    notify_slack(mon.get("slack_webhook_url"), msg)
    notify_telegram(mon.get("telegram_bot_token"), mon.get("telegram_chat_id"), msg)
