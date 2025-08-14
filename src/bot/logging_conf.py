from loguru import logger
from pathlib import Path

LOG_DIR = Path.cwd() / "logs"
LOG_DIR.mkdir(exist_ok=True)

logger.add(LOG_DIR / "bot.log", rotation="10 MB", retention=5)
