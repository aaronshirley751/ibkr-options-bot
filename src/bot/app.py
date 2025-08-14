from loguru import logger
import yaml
from pathlib import Path


def load_settings(path: str = "configs/settings.yaml") -> dict:
    p = Path(path)
    if not p.exists():
        return {}
    with open(p, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def main():
    logger.info("Starting ibkr-options-bot")
    settings = load_settings()

    # lazy import to avoid heavy deps at module import time
    from .broker.ibkr import IBKRBroker
    from .scheduler import run_scheduler

    broker = IBKRBroker(host=settings.get("broker", {}).get("host"), port=settings.get("broker", {}).get("port"), client_id=settings.get("broker", {}).get("client_id"), paper=not settings.get("broker", {}).get("read_only", False))

    try:
        run_scheduler(broker, settings)
    except KeyboardInterrupt:
        logger.info("Shutting down due to KeyboardInterrupt")
    finally:
        try:
            broker.disconnect()
        except Exception:
            pass


if __name__ == "__main__":
    main()
