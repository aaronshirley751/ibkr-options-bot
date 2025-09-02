from . import log as _log

logger = _log.logger
from .settings import get_settings


def main():
    logger.info("Starting ibkr-options-bot")
    settings = get_settings()

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
