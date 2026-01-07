"""Send a test Discord notification using the bot's monitoring utilities.

Usage examples:
- Set env var and run: DISCORD_WEBHOOK_URL=https://... python scripts/test_discord.py
- Or pass via CLI: python scripts/test_discord.py --webhook https://... --message "hello"
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.bot.monitoring import alert_all  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Send a test Discord webhook notification")
    parser.add_argument(
        "--webhook",
        help="Discord webhook URL (overrides DISCORD_WEBHOOK_URL env var)",
    )
    parser.add_argument(
        "--message",
        default="🤖 IBKR Bot test notification - Phase 1 dry-run starting",
        help="Message content to send",
    )
    parser.add_argument(
        "--username",
        default="IBKR Bot",
        help="Username to display in Discord",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    webhook = args.webhook or os.getenv("DISCORD_WEBHOOK_URL", "").strip()
    if not webhook:
        print("Missing webhook URL. Provide --webhook or set DISCORD_WEBHOOK_URL.")
        sys.exit(1)

    settings = {
        "monitoring": {
            "alerts_enabled": True,
            "discord_webhook_url": webhook,
            "discord_username": args.username,
        }
    }

    alert_all(settings, args.message)
    print("Sent Discord test notification.")


if __name__ == "__main__":
    main()
