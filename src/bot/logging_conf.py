from loguru import logger
from pathlib import Path
import json

LOG_DIR = Path.cwd() / "logs"
LOG_DIR.mkdir(exist_ok=True)

logger.add(LOG_DIR / "bot.log", rotation="10 MB", retention=5, enqueue=True)
logger.add(
	LOG_DIR / "bot.jsonl",
	rotation="10 MB",
	retention=5,
	serialize=True,  # JSON structure
	enqueue=True,
)
