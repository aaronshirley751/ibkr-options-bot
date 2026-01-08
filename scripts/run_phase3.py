#!/usr/bin/env python
"""
Phase 3 Execution Script
Runs the bot for extended dry-run with monitoring
"""
import subprocess
import sys
import time
from pathlib import Path
from datetime import datetime

def main():
    project_root = Path("c:\\Users\\tasms\\my-new-project\\Trading Bot\\ibkr-options-bot")
    venv_python = project_root / ".venv" / "Scripts" / "python.exe"
    
    print("=" * 70)
    print("PHASE 3 EXTENDED DRY-RUN - EXECUTION START")
    print("=" * 70)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Configuration: SPY only, 600s interval, Circuit breaker enabled")
    print(f"Target: 4+ hours (25+ cycles)")
    print(f"Dry-run: True (safe execution)")
    print()
    
    # Run the bot
    cmd = [str(venv_python), "-m", "src.bot.app"]
    print(f"Command: {' '.join(cmd)}")
    print()
    
    try:
        result = subprocess.run(cmd, cwd=str(project_root), timeout=14400)
        if result.returncode == 0:
            print("\n✅ Phase 3 completed successfully")
        else:
            print(f"\n⚠️ Phase 3 ended with code {result.returncode}")
    except subprocess.TimeoutExpired:
        print("\n⚠️ Phase 3 timeout after 4 hours (expected)")
    except KeyboardInterrupt:
        print("\n⚠️ Phase 3 interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
    
    print()
    print("=" * 70)
    print("PHASE 3 COMPLETED - CHECK LOGS FOR RESULTS")
    print("=" * 70)
    print(f"Logs: {project_root}/logs/bot.log")
    print(f"JSON: {project_root}/logs/bot.jsonl")

if __name__ == "__main__":
    main()
