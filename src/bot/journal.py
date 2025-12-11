import csv
import json
from pathlib import Path
from threading import Lock
from typing import Dict

LOG_DIR = Path.cwd() / "logs"
LOG_DIR.mkdir(exist_ok=True)

TRADES_CSV = LOG_DIR / "trades.csv"
TRADES_JSONL = LOG_DIR / "trades.jsonl"

CSV_HEADERS = ["timestamp", "symbol", "action", "quantity", "price", "stop", "target"]

_LOCK = Lock()


def log_trade(trade: Dict) -> None:
    """Record a trade (entry or exit) to both CSV and JSONL journal files.
    
    Thread-safe appending to trades.csv (tabular) and trades.jsonl (structured).
    Creates CSV header automatically on first write.
    
    Args:
        trade: Dictionary with keys: timestamp, symbol, action, quantity, price, stop, target.
               Extra fields are preserved in JSONL but omitted from CSV.
    
    Returns:
        None
    
    Example:
        >>> log_trade({
        ...     "timestamp": "2025-12-10T14:30:00+00:00",
        ...     "symbol": "SPY",
        ...     "action": "BUY_CALL",
        ...     "quantity": 3,
        ...     "price": 2.50,
        ...     "stop": "1.25",
        ...     "target": "3.50",
        ... })
    """
    with _LOCK:
        if not TRADES_CSV.exists():
            with open(TRADES_CSV, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
                writer.writeheader()
        with open(TRADES_CSV, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
            writer.writerow({k: trade.get(k, "") for k in CSV_HEADERS})
        with open(TRADES_JSONL, "a", encoding="utf-8") as f:
            f.write(json.dumps(trade, default=str) + "\n")
