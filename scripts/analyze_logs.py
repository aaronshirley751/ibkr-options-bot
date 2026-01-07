"""Analyze bot logs from extended dry-run.

Usage:
    python scripts/analyze_logs.py --bot-log logs/bot_20260107_120000.log
    python scripts/analyze_logs.py --jsonl logs/bot.jsonl
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path


def parse_text_log(log_path: Path) -> dict:
    """Parse text log file and extract statistics."""
    stats = {
        "total_lines": 0,
        "by_level": Counter(),
        "signals": Counter(),
        "symbols_processed": Counter(),
        "errors": [],
        "warnings": [],
        "cycle_count": 0,
        "timestamps": {"first": None, "last": None},
    }

    with log_path.open("r", encoding="utf-8") as f:
        for line in f:
            stats["total_lines"] += 1

            # Extract log level
            if " | INFO" in line:
                stats["by_level"]["INFO"] += 1
            elif " | WARNING" in line:
                stats["by_level"]["WARNING"] += 1
                stats["warnings"].append(line.strip()[-100:])  # Last 100 chars
            elif " | ERROR" in line:
                stats["by_level"]["ERROR"] += 1
                stats["errors"].append(line.strip()[-100:])
            elif " | DEBUG" in line:
                stats["by_level"]["DEBUG"] += 1

            # Extract timestamp
            match = re.search(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", line)
            if match:
                ts = match.group(1)
                if not stats["timestamps"]["first"]:
                    stats["timestamps"]["first"] = ts
                stats["timestamps"]["last"] = ts

            # Extract signals
            if "signal=" in line or '"signal"' in line:
                for sig in ["BUY", "SELL", "HOLD"]:
                    if sig in line:
                        stats["signals"][sig] += 1

            # Extract symbols
            if "symbol=" in line:
                match = re.search(r'symbol=(\w+)', line)
                if match:
                    stats["symbols_processed"][match.group(1)] += 1

            # Count cycles
            if "Cycle decision" in line or "run_cycle" in line:
                stats["cycle_count"] += 1

    return stats


def parse_jsonl_log(log_path: Path) -> dict:
    """Parse JSONL log file and extract statistics."""
    stats = {
        "total_lines": 0,
        "by_level": Counter(),
        "by_event": Counter(),
        "signals": Counter(),
        "symbols_processed": Counter(),
        "errors": [],
        "warnings": [],
        "timestamps": {"first": None, "last": None},
    }

    with log_path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            stats["total_lines"] += 1
            try:
                entry = json.loads(line)
                level = entry.get("level", "UNKNOWN")
                stats["by_level"][level] += 1

                # Event type
                if "event" in entry:
                    stats["by_event"][entry["event"]] += 1

                # Timestamps
                if "timestamp" in entry:
                    ts = entry["timestamp"]
                    if not stats["timestamps"]["first"]:
                        stats["timestamps"]["first"] = ts
                    stats["timestamps"]["last"] = ts

                # Signals
                if "signal" in entry:
                    stats["signals"][entry["signal"]] += 1

                # Symbols
                if "symbol" in entry:
                    stats["symbols_processed"][entry["symbol"]] += 1

                # Errors/warnings
                if level == "ERROR":
                    stats["errors"].append(entry.get("message", ""))
                elif level == "WARNING":
                    stats["warnings"].append(entry.get("message", ""))
            except json.JSONDecodeError:
                pass

    return stats


def main():
    parser = argparse.ArgumentParser(description="Analyze bot logs from extended dry-run")
    parser.add_argument("--bot-log", type=Path, help="Text log file from bot")
    parser.add_argument("--jsonl", type=Path, help="JSONL log file from bot")
    parser.add_argument("--output", type=Path, help="Output summary file (default: stdout)")
    args = parser.parse_args()

    if not args.bot_log and not args.jsonl:
        parser.print_help()
        return

    stats = {}
    if args.bot_log:
        if not args.bot_log.exists():
            print(f"ERROR: {args.bot_log} not found")
            return
        stats = parse_text_log(args.bot_log)
    elif args.jsonl:
        if not args.jsonl.exists():
            print(f"ERROR: {args.jsonl} not found")
            return
        stats = parse_jsonl_log(args.jsonl)

    # Generate report
    report = []
    report.append("=" * 60)
    report.append("Extended Dry-Run Log Analysis")
    report.append("=" * 60)
    report.append("")

    # Summary
    report.append("Summary:")
    report.append(f"  Total log lines: {stats['total_lines']}")
    report.append(
        f"  Timespan: {stats['timestamps']['first']} to {stats['timestamps']['last']}"
    )
    if stats.get("cycle_count"):
        report.append(f"  Cycles completed: {stats['cycle_count']}")
    report.append("")

    # Log levels
    report.append("Log Levels:")
    for level, count in sorted(stats["by_level"].items(), key=lambda x: -x[1]):
        report.append(f"  {level}: {count}")
    report.append("")

    # Signals
    if stats["signals"]:
        report.append("Signals Generated:")
        for sig, count in sorted(stats["signals"].items(), key=lambda x: -x[1]):
            report.append(f"  {sig}: {count}")
        report.append("")

    # Symbols
    if stats["symbols_processed"]:
        report.append("Symbols Processed:")
        for sym, count in sorted(stats["symbols_processed"].items(), key=lambda x: -x[1]):
            report.append(f"  {sym}: {count} times")
        report.append("")

    # Events (JSONL only)
    if stats.get("by_event"):
        report.append("Events:")
        for evt, count in sorted(stats["by_event"].items(), key=lambda x: -x[1]):
            report.append(f"  {evt}: {count}")
        report.append("")

    # Errors
    if stats["errors"]:
        report.append(f"Errors ({len(stats['errors'])} total):")
        for err in stats["errors"][:10]:  # First 10
            report.append(f"  - {err[:80]}")
        if len(stats["errors"]) > 10:
            report.append(f"  ... and {len(stats['errors']) - 10} more")
        report.append("")

    # Warnings
    if stats["warnings"]:
        report.append(f"Warnings ({len(stats['warnings'])} total):")
        for warn in stats["warnings"][:10]:
            report.append(f"  - {warn[:80]}")
        if len(stats["warnings"]) > 10:
            report.append(f"  ... and {len(stats['warnings']) - 10} more")
        report.append("")

    report.append("=" * 60)

    # Output
    output = "\n".join(report)
    print(output)

    if args.output:
        args.output.write_text(output)
        print(f"\nReport saved to: {args.output}")


if __name__ == "__main__":
    main()
