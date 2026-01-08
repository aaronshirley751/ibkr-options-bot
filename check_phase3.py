#!/usr/bin/env python3
"""
Phase 3 Quick Status Check - Shows current bot status
Use this to check Phase 3 progress at any time
"""

import sys
from pathlib import Path
from datetime import datetime

BOT_LOG = Path("logs/phase3_bot_output.log")

def show_status():
    """Show Phase 3 status"""
    
    print("=" * 70)
    print(f"PHASE 3 STATUS CHECK - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    if not BOT_LOG.exists():
        print("❌ Bot log not found. Is Phase 3 running?")
        return
    
    # Read recent log lines
    with open(BOT_LOG, 'r') as f:
        lines = f.readlines()
    
    # Count key events
    cycles = sum(1 for line in lines if "Cycle decision" in line)
    symbols_processed = sum(1 for line in lines if "would place order" in line)
    errors = sum(1 for line in lines if "ERROR" in line)
    warnings = sum(1 for line in lines if "WARNING" in line and "disconnected" not in line.lower())
    reconnects = sum(1 for line in lines if "reconnected successfully" in line)
    
    # Get recent lines
    recent = lines[-15:] if len(lines) > 15 else lines
    
    print(f"\n📊 Metrics:")
    print(f"  Cycles Detected:     {cycles}")
    print(f"  Symbols Processed:   {symbols_processed}")
    print(f"  Reconnects:          {reconnects}")
    print(f"  Warnings:            {warnings}")
    print(f"  Errors:              {errors}")
    
    print(f"\n📝 Recent Activity (last 15 lines):")
    print("-" * 70)
    for line in recent:
        print(line.rstrip())
    
    print("\n" + "=" * 70)
    
    # Status assessment
    if errors == 0 and cycles > 0:
        print("✅ Phase 3 running normally")
    elif errors > 0:
        print(f"⚠️  {errors} errors detected - review logs")
    else:
        print("⏳ Waiting for first cycle...")
    
    print("=" * 70)

if __name__ == "__main__":
    show_status()
