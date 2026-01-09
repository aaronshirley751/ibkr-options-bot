import os
import signal
import sys
import threading

from . import log as _log

# Initialize logging sinks (file + JSON) via side-effect import
# Ensures logs/bot.log and logs/bot.jsonl are created for long runs
from . import logging_conf as _logging_conf  # noqa: F401

logger = _log.logger
from .settings import get_settings


def main():
    logger.info("Starting ibkr-options-bot")
    settings = get_settings()

    # Startup validation for safe deployment
    logger.info("Validating configuration...")
    if not settings.dry_run:
        logger.warning("⚠ dry_run is FALSE - orders will be live")
    else:
        logger.info("✓ dry_run mode enabled (paper trading)")

    if not settings.symbols:
        logger.error("No symbols configured; exiting")
        return
    logger.info(f"✓ Symbols configured: {settings.symbols}")

    try:
        logger.info(
            f"✓ Risk settings: max_daily_loss={settings.risk.max_daily_loss_pct * 100:.1f}%"
            f", max_risk_per_trade={settings.risk.max_risk_pct_per_trade * 100:.1f}%"
        )
    except Exception as risk_err:  # pylint: disable=broad-except
        logger.warning(f"Risk settings not fully available: {risk_err}")

    alert_channels = []
    mon = settings.monitoring
    if mon.alerts_enabled:
        if mon.discord_webhook_url:
            alert_channels.append("Discord")
        if mon.slack_webhook_url:
            alert_channels.append("Slack")
        if mon.telegram_bot_token:
            alert_channels.append("Telegram")
        logger.info(f"✓ Alerts enabled: {', '.join(alert_channels) or 'none configured'}")
    else:
        logger.info("ℹ Alerts disabled")

    logger.info("Configuration validation complete")

    # Setup signal handlers for graceful shutdown (with optional ignore)
    shutdown_event = threading.Event()
    ignore_signals = os.getenv("BOT_IGNORE_SIGNALS", "").lower() in {"1", "true", "yes"}
    connecting = True  # Flag to prevent shutdown during connection phase

    def handle_shutdown(signum, frame):
        nonlocal connecting
        try:
            sig_name = signal.Signals(signum).name  # richer logging to diagnose unexpected signals
        except Exception:
            sig_name = str(signum)

        if connecting:
            logger.warning(f"Shutdown signal received during connection phase, deferring: {signum} ({sig_name})")
            return

        if ignore_signals:
            logger.warning(f"Shutdown signal received but ignored due to BOT_IGNORE_SIGNALS: {signum} ({sig_name})")
            return

        logger.info(f"Shutdown signal received: {signum} ({sig_name})")
        shutdown_event.set()

    signal.signal(signal.SIGTERM, handle_shutdown)
    signal.signal(signal.SIGINT, handle_shutdown)

    # Auto-reset daily loss guard if configured (dry-run testing convenience)
    if settings.risk.reset_daily_guard_on_start:
        logger.info("Auto-resetting daily loss guard (reset_daily_guard_on_start=True)")
        from .risk import reset_daily_loss_guard
        try:
            reset_daily_loss_guard()
            logger.info("✓ Daily loss guard cleared for today")
        except Exception as reset_err:  # pylint: disable=broad-except
            logger.warning(f"Failed to reset daily loss guard: {reset_err}")

    # lazy import to avoid heavy deps at module import time
    from .broker.ibkr import IBKRBroker
    from .scheduler import run_scheduler

    broker = IBKRBroker(
        host=settings.broker.host,
        port=settings.broker.port,
        client_id=settings.broker.client_id,
        paper=not settings.broker.read_only,
    )

    # Connect to Gateway before entering scheduler loop
    logger.info(f"Connecting to Gateway at {settings.broker.host}:{settings.broker.port}...")
    try:
        broker.connect()
        connecting = False  # Signal handler can now respond to shutdown signals
        logger.info("✓ Gateway connected successfully")
    except Exception as conn_err:  # pylint: disable=broad-except
        connecting = False
        logger.error(f"Failed to connect to Gateway: {conn_err}")
        return

    try:
        # Pass dict-like view for now; scheduler will accept either object or dict
        run_scheduler(broker, settings.model_dump(), stop_event=shutdown_event)
    except KeyboardInterrupt:
        logger.info("Shutting down due to KeyboardInterrupt")
    finally:
        try:
            broker.disconnect()
        except Exception:  # pylint: disable=broad-except
            pass


if __name__ == "__main__":
    main()
