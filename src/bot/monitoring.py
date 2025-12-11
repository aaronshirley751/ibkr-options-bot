def _http_post(
    url: str, payload: dict, headers: Optional[dict] = None, timeout: int = 10
) -> bool:
    """Send JSON POST request to webhook URL with error handling.
    
    Low-level utility for HTTP communication with external services (Slack, Telegram, etc).
    Returns True/False based on response status, never raises exceptions.
    
    Args:
        url: Full webhook URL to POST to (e.g., Slack incoming webhook, Telegram bot API).
        payload: Dictionary to JSON-encode and send as request body.
        headers: Optional dict of additional HTTP headers to include.
        timeout: Timeout in seconds for the HTTP request (default 10).
    
    Returns:
        True if response status is 200-299, False otherwise or on any error.
    """
def send_heartbeat(heartbeat_url: Optional[str]) -> None:
    """Send GET request to heartbeat monitoring service (e.g., healthchecks.io).
    
    Signals external health monitoring that the bot is running. Commonly used with
    Healthchecks.io or similar services to detect when the bot stops responding.
    
    Args:
        heartbeat_url: Full URL to GET ping (or None to skip). Should include unique ID.
                      Example: "https://hc-ping.com/12345678-1234-1234-1234-123456789012"
    
    Returns:
        None (failures logged at debug level)
    """
def notify_slack(webhook_url: Optional[str], message: str) -> None:
    """Send text message to Slack channel via incoming webhook.
    
    Posts a simple text message to a Slack channel. Webhook should be configured
    to accept plain text payloads.
    
    Args:
        webhook_url: Slack incoming webhook URL (or None to skip).
                    Example: "https://hooks.slack.com/services/T.../B.../X..."
        message: Text message body to send.
    
    Returns:
        None (failures logged at debug level)
    """
def notify_telegram(
    bot_token: Optional[str], chat_id: Optional[str], message: str
) -> None:
    """Send message to Telegram chat via bot token and chat ID.
    
    Uses Telegram Bot API sendMessage endpoint to deliver text alerts.
    
    Args:
        bot_token: Telegram bot token from BotFather (or None to skip).
                  Format: "123456789:ABCdEfGhIjKlMnOpQrStUvWxYz"
        chat_id: Telegram chat ID or user ID (or None to skip).
        message: Text message body to send.
    
    Returns:
        None (failures logged at debug level)
    """
def alert_all(settings: dict, message: str) -> None:
    """Send alert message to all configured notification channels (Slack, Telegram).
    
    Convenience function that dispatches a single message to all enabled alerting
    services simultaneously. Failures in one service don't block others.
    
    Args:
        settings: Configuration dict with nested key 'monitoring' containing:
                 - alerts_enabled (bool): Master switch for all alerts
                 - slack_webhook_url (str or None): Slack webhook URL
                 - telegram_bot_token (str or None): Telegram bot token
                 - telegram_chat_id (str or None): Telegram chat ID
        message: Alert message text to send to all channels.
    
    Returns:
        None
    
    Example:
        >>> settings = {
        ...     "monitoring": {
        ...         "alerts_enabled": True,
        ...         "slack_webhook_url": "https://hooks.slack.com/...",
        ...         "telegram_bot_token": "123456:ABC...",
        ...         "telegram_chat_id": "9876543210",
        ...     }
        ... }
        >>> alert_all(settings, "Critical: Daily loss limit reached")
    """
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
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with request.urlopen(req, timeout=timeout) as resp:  # nosec B310
            return 200 <= resp.getcode() < 300
    except Exception as e:  # pylint: disable=broad-except
        logger.debug(f"HTTP POST failed to {url}: {e}")
        return False


def send_heartbeat(heartbeat_url: Optional[str]) -> None:
    if not heartbeat_url:
        return
    try:
        # For healthchecks.io, a simple GET is typical; support POST too
        req = request.Request(heartbeat_url, method="GET")
        with request.urlopen(req, timeout=5) as resp:  # nosec B310
            _ = resp.read()
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


def alert_all(settings: dict, message: str) -> None:
    mon = settings.get("monitoring", {})
    if not mon or mon.get("alerts_enabled") is False:
        return
    notify_slack(mon.get("slack_webhook_url"), message)
    notify_telegram(mon.get("telegram_bot_token"), mon.get("telegram_chat_id"), message)
