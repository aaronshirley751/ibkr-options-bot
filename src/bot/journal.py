import csv
import json
from pathlib import Path
from typing import Dict

LOG_DIR = Path.cwd() / "logs"
LOG_DIR.mkdir(exist_ok=True)

TRADES_CSV = LOG_DIR / "trades.csv"
TRADES_JSONL = LOG_DIR / "trades.jsonl"

CSV_HEADERS = ["timestamp", "symbol", "action", "quantity", "price", "stop", "target"]


def log_trade(trade: Dict):
    if not TRADES_CSV.exists():
        with open(TRADES_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
            writer.writeheader()
    with open(TRADES_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
        writer.writerow({k: trade.get(k, "") for k in CSV_HEADERS})
    with open(TRADES_JSONL, "a", encoding="utf-8") as f:
        f.write(json.dumps(trade, default=str) + "\n")
