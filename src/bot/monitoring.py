from __future__ import annotations

import json
from typing import Optional
from urllib import request
from .log import logger


def _http_post(url: str, payload: dict, headers: Optional[dict] = None, timeout: int = 10) -> bool:
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


def notify_telegram(bot_token: Optional[str], chat_id: Optional[str], message: str) -> None:
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
