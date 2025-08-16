from . import log as _log
logger = _log.logger
from pathlib import Path

LOG_DIR = Path.cwd() / "logs"
LOG_DIR.mkdir(exist_ok=True)

try:
    # These attributes exist on loguru logger; stdlib fallback will raise AttributeError
    logger.add(LOG_DIR / "bot.log", rotation="10 MB", retention=5, enqueue=True)  # type: ignore[attr-defined]
    logger.add(  # type: ignore[attr-defined]
        LOG_DIR / "bot.jsonl",
        rotation="10 MB",
        retention=5,
        serialize=True,  # JSON structure
        enqueue=True,
    )
except (AttributeError, TypeError):  # pragma: no cover
    # Fallback logger doesn't support .add; ignore advanced sinks
    pass
