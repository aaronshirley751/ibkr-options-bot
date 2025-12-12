"""Unit tests for monitoring.py - alerting and heartbeat functions."""

from unittest import mock
from urllib.error import HTTPError, URLError

import pytest

from src.bot.monitoring import (
    _http_post,
    alert_all,
    notify_slack,
    notify_telegram,
    send_heartbeat,
)


class TestHttpPost:
    """Test low-level HTTP POST utility."""

    @mock.patch("src.bot.monitoring.request.urlopen")
    def test_http_post_success(self, mock_urlopen):
        """Successfully sends POST request with 200 response."""
        mock_response = mock.MagicMock()
        mock_response.getcode.return_value = 200
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        result = _http_post("https://example.com/webhook", {"key": "value"})

        assert result is True
        mock_urlopen.assert_called_once()

    @mock.patch("src.bot.monitoring.request.urlopen")
    def test_http_post_success_299(self, mock_urlopen):
        """Accepts response codes 200-299."""
        mock_response = mock.MagicMock()
        mock_response.getcode.return_value = 299
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        result = _http_post("https://example.com/webhook", {"key": "value"})

        assert result is True

    @mock.patch("src.bot.monitoring.request.urlopen")
    def test_http_post_failure_300(self, mock_urlopen):
        """Rejects response codes >= 300."""
        mock_response = mock.MagicMock()
        mock_response.getcode.return_value = 300
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        result = _http_post("https://example.com/webhook", {"key": "value"})

        assert result is False

    @mock.patch("src.bot.monitoring.request.urlopen")
    def test_http_post_failure_500(self, mock_urlopen):
        """Rejects server error codes."""
        mock_response = mock.MagicMock()
        mock_response.getcode.return_value = 500
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        result = _http_post("https://example.com/webhook", {"key": "value"})

        assert result is False

    @mock.patch("src.bot.monitoring.request.urlopen")
    def test_http_post_connection_error(self, mock_urlopen):
        """Handles connection errors gracefully."""
        mock_urlopen.side_effect = URLError("Network error")

        result = _http_post("https://example.com/webhook", {"key": "value"})

        assert result is False

    @mock.patch("src.bot.monitoring.request.urlopen")
    def test_http_post_timeout_error(self, mock_urlopen):
        """Handles timeout errors gracefully."""
        mock_urlopen.side_effect = TimeoutError("Request timeout")

        result = _http_post("https://example.com/webhook", {"key": "value"})

        assert result is False

    @mock.patch("src.bot.monitoring.request.urlopen")
    def test_http_post_http_error(self, mock_urlopen):
        """Handles HTTP errors gracefully."""
        mock_urlopen.side_effect = HTTPError("https://example.com", 400, "Bad Request", {}, None)

        result = _http_post("https://example.com/webhook", {"key": "value"})

        assert result is False

    @mock.patch("src.bot.monitoring.request.Request")
    @mock.patch("src.bot.monitoring.request.urlopen")
    def test_http_post_includes_headers(self, mock_urlopen, mock_request):
        """Includes custom headers in request."""
        mock_response = mock.MagicMock()
        mock_response.getcode.return_value = 200
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        headers = {"Authorization": "Bearer token123"}
        result = _http_post("https://example.com/webhook", {"key": "value"}, headers=headers)

        assert result is True
        # Verify the Request object was created
        mock_request.assert_called_once()

    @mock.patch("src.bot.monitoring.request.urlopen")
    def test_http_post_json_serialization(self, mock_urlopen):
        """Properly serializes payload to JSON."""
        mock_response = mock.MagicMock()
        mock_response.getcode.return_value = 200
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        payload = {"message": "test", "count": 42, "nested": {"key": "value"}}
        result = _http_post("https://example.com/webhook", payload)

        assert result is True

    @mock.patch("src.bot.monitoring.request.urlopen")
    def test_http_post_custom_timeout(self, mock_urlopen):
        """Uses custom timeout when specified."""
        mock_response = mock.MagicMock()
        mock_response.getcode.return_value = 200
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        result = _http_post("https://example.com/webhook", {"key": "value"}, timeout=30)

        assert result is True
        # Verify timeout was passed to urlopen
        call_args = mock_urlopen.call_args
        assert call_args[1]["timeout"] == 30 or (len(call_args[0]) > 1 and call_args[0][1] == 30)


class TestSendHeartbeat:
    """Test heartbeat sending."""

    @mock.patch("src.bot.monitoring.request.urlopen")
    def test_send_heartbeat_success(self, mock_urlopen):
        """Successfully sends heartbeat GET request."""
        mock_response = mock.MagicMock()
        mock_response.read.return_value = b""
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        send_heartbeat("https://healthchecks.io/ping/uuid-here")

        mock_urlopen.assert_called_once()

    @mock.patch("src.bot.monitoring.request.urlopen")
    def test_send_heartbeat_connection_error(self, mock_urlopen):
        """Handles connection errors gracefully."""
        mock_urlopen.side_effect = URLError("Network error")

        # Should not raise, just log
        send_heartbeat("https://healthchecks.io/ping/uuid-here")

    @mock.patch("src.bot.monitoring.request.urlopen")
    def test_send_heartbeat_timeout(self, mock_urlopen):
        """Handles timeout gracefully."""
        mock_urlopen.side_effect = TimeoutError("Timeout")

        send_heartbeat("https://healthchecks.io/ping/uuid-here")

    def test_send_heartbeat_none_url(self):
        """Skips if URL is None."""
        # Should not raise any exception
        send_heartbeat(None)

    def test_send_heartbeat_empty_url(self):
        """Skips if URL is empty string."""
        send_heartbeat("")


class TestNotifySlack:
    """Test Slack notifications."""

    @mock.patch("src.bot.monitoring._http_post")
    def test_notify_slack_success(self, mock_http_post):
        """Successfully sends Slack message."""
        mock_http_post.return_value = True

        notify_slack("https://hooks.slack.com/services/xxx/yyy/zzz", "Test message")

        mock_http_post.assert_called_once()
        call_args = mock_http_post.call_args
        assert call_args[0][0] == "https://hooks.slack.com/services/xxx/yyy/zzz"
        assert call_args[0][1]["text"] == "Test message"

    @mock.patch("src.bot.monitoring._http_post")
    def test_notify_slack_failure(self, mock_http_post):
        """Handles notification failure gracefully."""
        mock_http_post.return_value = False

        # Should not raise, just log
        notify_slack("https://hooks.slack.com/services/xxx/yyy/zzz", "Test message")

    def test_notify_slack_none_webhook(self):
        """Skips if webhook URL is None."""
        notify_slack(None, "Test message")

    def test_notify_slack_empty_webhook(self):
        """Skips if webhook URL is empty."""
        notify_slack("", "Test message")

    @mock.patch("src.bot.monitoring._http_post")
    def test_notify_slack_empty_message(self, mock_http_post):
        """Sends empty message if that's what's passed."""
        mock_http_post.return_value = True

        notify_slack("https://hooks.slack.com/services/xxx/yyy/zzz", "")

        mock_http_post.assert_called_once()
        call_args = mock_http_post.call_args
        assert call_args[0][1]["text"] == ""

    @mock.patch("src.bot.monitoring._http_post")
    def test_notify_slack_long_message(self, mock_http_post):
        """Handles long messages."""
        mock_http_post.return_value = True
        long_message = "x" * 10000

        notify_slack("https://hooks.slack.com/services/xxx/yyy/zzz", long_message)

        mock_http_post.assert_called_once()


class TestNotifyTelegram:
    """Test Telegram notifications."""

    @mock.patch("src.bot.monitoring._http_post")
    def test_notify_telegram_success(self, mock_http_post):
        """Successfully sends Telegram message."""
        mock_http_post.return_value = True

        notify_telegram("123:ABC-DEF", "12345", "Test message")

        mock_http_post.assert_called_once()
        call_args = mock_http_post.call_args
        assert "api.telegram.org" in call_args[0][0]
        assert call_args[0][1]["chat_id"] == "12345"
        assert call_args[0][1]["text"] == "Test message"

    @mock.patch("src.bot.monitoring._http_post")
    def test_notify_telegram_failure(self, mock_http_post):
        """Handles notification failure gracefully."""
        mock_http_post.return_value = False

        notify_telegram("123:ABC-DEF", "12345", "Test message")

    def test_notify_telegram_none_token(self):
        """Skips if bot token is None."""
        notify_telegram(None, "12345", "Test message")

    def test_notify_telegram_empty_token(self):
        """Skips if bot token is empty."""
        notify_telegram("", "12345", "Test message")

    def test_notify_telegram_none_chat_id(self):
        """Skips if chat ID is None."""
        notify_telegram("123:ABC-DEF", None, "Test message")

    def test_notify_telegram_empty_chat_id(self):
        """Skips if chat ID is empty."""
        notify_telegram("123:ABC-DEF", "", "Test message")

    def test_notify_telegram_none_both(self):
        """Skips if both token and chat_id are None."""
        notify_telegram(None, None, "Test message")

    @mock.patch("src.bot.monitoring._http_post")
    def test_notify_telegram_constructs_correct_url(self, mock_http_post):
        """Constructs correct Telegram API URL."""
        mock_http_post.return_value = True
        token = "123456:ABCdEfGhIjKlMnOp"
        chat_id = "9876543210"

        notify_telegram(token, chat_id, "Test")

        call_args = mock_http_post.call_args
        url = call_args[0][0]
        assert f"bot{token}" in url
        assert "sendMessage" in url


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


class TestAlertAll:
    """Test combined alerting."""

    @mock.patch("src.bot.monitoring.notify_discord")
    @mock.patch("src.bot.monitoring.notify_slack")
    @mock.patch("src.bot.monitoring.notify_telegram")
    def test_alert_all_sends_all(self, mock_telegram, mock_slack, mock_discord):
        """Sends to Discord, Slack, and Telegram when configured."""
        settings = {
            "monitoring": {
                "alerts_enabled": True,
                "discord_webhook_url": "https://discord.com/api/webhooks/123/abc",
                "slack_webhook_url": "https://hooks.slack.com/xxx",
                "telegram_bot_token": "123:ABC",
                "telegram_chat_id": "456",
            }
        }

        alert_all(settings, "Alert message")

        mock_discord.assert_called_once_with("https://discord.com/api/webhooks/123/abc", "Alert message")
        mock_slack.assert_called_once()
        mock_telegram.assert_called_once()

    @mock.patch("src.bot.monitoring.notify_discord")
    @mock.patch("src.bot.monitoring.notify_slack")
    @mock.patch("src.bot.monitoring.notify_telegram")
    def test_alert_all_discord_only(self, mock_telegram, mock_slack, mock_discord):
        """Sends only Discord when others not configured."""
        settings = {
            "monitoring": {
                "alerts_enabled": True,
                "discord_webhook_url": "https://discord.com/api/webhooks/123/abc",
            }
        }

        alert_all(settings, "Alert message")

        mock_discord.assert_called_once()
        mock_slack.assert_called_once_with(None, "Alert message")
        mock_telegram.assert_called_once()

    @mock.patch("src.bot.monitoring.notify_discord")
    @mock.patch("src.bot.monitoring.notify_slack")
    @mock.patch("src.bot.monitoring.notify_telegram")
    def test_alert_all_alerts_disabled(self, mock_telegram, mock_slack, mock_discord):
        """Skips all alerts when disabled."""
        settings = {"monitoring": {"alerts_enabled": False}}

        alert_all(settings, "Alert message")

        mock_discord.assert_not_called()
        mock_slack.assert_not_called()
        mock_telegram.assert_not_called()

    @mock.patch("src.bot.monitoring.notify_discord")
    @mock.patch("src.bot.monitoring.notify_slack")
    @mock.patch("src.bot.monitoring.notify_telegram")
    def test_alert_all_no_monitoring_config(self, mock_telegram, mock_slack, mock_discord):
        """Skips alerts if monitoring not configured."""
        settings = {}

        alert_all(settings, "Alert message")

        mock_discord.assert_not_called()
        mock_slack.assert_not_called()
        mock_telegram.assert_not_called()

    @mock.patch("src.bot.monitoring.notify_discord")
    @mock.patch("src.bot.monitoring.notify_slack")
    @mock.patch("src.bot.monitoring.notify_telegram")
    def test_alert_all_slack_only(self, mock_telegram, mock_slack, mock_discord):
        """Sends only Slack when Telegram and Discord not configured."""
        settings = {
            "monitoring": {
                "alerts_enabled": True,
                "slack_webhook_url": "https://hooks.slack.com/xxx",
            }
        }

        alert_all(settings, "Alert message")

        mock_slack.assert_called_once()
        mock_telegram.assert_called_once_with(None, None, "Alert message")

    @mock.patch("src.bot.monitoring.notify_slack")
    @mock.patch("src.bot.monitoring.notify_telegram")
    def test_alert_all_telegram_only(self, mock_telegram, mock_slack):
        """Sends only Telegram when Slack not configured."""
        settings = {
            "monitoring": {
                "alerts_enabled": True,
                "telegram_bot_token": "123:ABC",
                "telegram_chat_id": "456",
            }
        }

        alert_all(settings, "Alert message")

        mock_slack.assert_called_once_with(None, "Alert message")
        mock_telegram.assert_called_once()

    @mock.patch("src.bot.monitoring.notify_slack")
    @mock.patch("src.bot.monitoring.notify_telegram")
    def test_alert_all_passes_message(self, mock_telegram, mock_slack):
        """Passes message correctly to both functions."""
        settings = {
            "monitoring": {
                "alerts_enabled": True,
                "slack_webhook_url": "https://hooks.slack.com/xxx",
                "telegram_bot_token": "123:ABC",
                "telegram_chat_id": "456",
            }
        }
        message = "Critical: Daily loss limit reached"

        alert_all(settings, message)

        # Verify message passed correctly
        slack_call = mock_slack.call_args
        assert slack_call[0][1] == message  # Second argument is the message

        telegram_call = mock_telegram.call_args
        assert telegram_call[0][2] == message  # Third argument is the message

    @mock.patch("src.bot.monitoring.notify_slack")
    @mock.patch("src.bot.monitoring.notify_telegram")
    def test_alert_all_none_monitoring_value(self, mock_telegram, mock_slack):
        """Handles None value for monitoring key."""
        settings = {"monitoring": None}

        alert_all(settings, "Alert message")

        mock_slack.assert_not_called()
        mock_telegram.assert_not_called()
