import signal
import sys

from . import log as _log

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
    logger.info("✓ Symbols configured: %s", settings.symbols)

    try:
        logger.info(
            "✓ Risk settings: max_daily_loss=%.1f%%, max_risk_per_trade=%.1f%%",
            settings.risk.max_daily_loss_pct * 100,
            settings.risk.max_risk_pct_per_trade * 100,
        )
    except Exception as risk_err:  # pylint: disable=broad-except
        logger.warning("Risk settings not fully available: %s", risk_err)

    alert_channels = []
    mon = settings.monitoring
    if mon.alerts_enabled:
        if mon.discord_webhook_url:
            alert_channels.append("Discord")
        if mon.slack_webhook_url:
            alert_channels.append("Slack")
        if mon.telegram_bot_token:
            alert_channels.append("Telegram")
        logger.info("✓ Alerts enabled: %s", ", ".join(alert_channels) or "none configured")
    else:
        logger.info("ℹ Alerts disabled")

    logger.info("Configuration validation complete")

    # Setup signal handlers for graceful shutdown
    shutdown_requested = False
    
    def handle_shutdown(signum, frame):
        nonlocal shutdown_requested
        logger.info("Shutdown signal received (signal %s)", signum)
        shutdown_requested = True
        sys.exit(0)
    
    signal.signal(signal.SIGTERM, handle_shutdown)
    signal.signal(signal.SIGINT, handle_shutdown)

    # lazy import to avoid heavy deps at module import time
    from .broker.ibkr import IBKRBroker
    from .scheduler import run_scheduler

    broker = IBKRBroker(
        host=settings.broker.host,
        port=settings.broker.port,
        client_id=settings.broker.client_id,
        paper=not settings.broker.read_only,
    )

    try:
        # Pass dict-like view for now; scheduler will accept either object or dict
        run_scheduler(broker, settings.model_dump())
    except KeyboardInterrupt:
        logger.info("Shutting down due to KeyboardInterrupt")
    finally:
        try:
            broker.disconnect()
        except Exception:  # pylint: disable=broad-except
            pass


if __name__ == "__main__":
    main()
