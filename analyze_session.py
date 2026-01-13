#!/usr/bin/env python
"""
Real-time log analysis script for session monitoring.
Extracts key metrics from bot.log as the bot runs.
"""

import re
import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict

def parse_log_file(log_file):
    """Parse bot.log and extract metrics."""
    
    if not log_file.exists():
        print(f"❌ Log file not found: {log_file}")
        return
    
    metrics = {
        "cycles": [],
        "contract_qualifications": [],
        "hist_requests": [],
        "fallbacks": [],
        "errors": [],
    }
    
    with open(log_file, 'r') as f:
        lines = f.readlines()
    
    current_cycle = None
    
    for line in lines:
        # Track cycle starts
        if "Starting cycle" in line or "run_cycle:" in line:
            match = re.search(r"cycle_count[\":\s]+(\d+)", line)
            if match:
                current_cycle = int(match.group(1))
                metrics["cycles"].append({
                    "cycle": current_cycle,
                    "timestamp": line[:19],
                    "symbols": [],
                })
        
        # Contract qualification
        if "Contract qualified" in line or "conId" in line:
            match = re.search(r"conId[\":\s=]+(\d+)", line)
            if match:
                symbol = None
                if "SPY" in line:
                    symbol = "SPY"
                elif "QQQ" in line:
                    symbol = "QQQ"
                metrics["contract_qualifications"].append({
                    "symbol": symbol,
                    "conId": match.group(1),
                    "timestamp": line[:19],
                })
                print(f"✅ Contract qualified: {symbol} (conId={match.group(1)})")
        
        # Historical data requests
        if "[HIST] Completed" in line or "historical" in line.lower():
            # Extract elapsed time
            elapsed_match = re.search(r"elapsed[\":\s=]+([0-9.]+)s", line)
            # Extract bar count
            bars_match = re.search(r"bars[\":\s=]+(\d+)", line)
            
            if elapsed_match and bars_match:
                elapsed = float(elapsed_match.group(1))
                bars = int(bars_match.group(1))
                symbol = None
                for s in ["SPY", "QQQ"]:
                    if s in line:
                        symbol = s
                        break
                
                metrics["hist_requests"].append({
                    "symbol": symbol,
                    "elapsed": elapsed,
                    "bars": bars,
                    "timestamp": line[:19],
                })
                status = "✅" if bars > 0 else "❌"
                print(f"{status} [HIST] {symbol}: elapsed={elapsed:.2f}s, bars={bars}")
        
        # Fallback usage
        if "fallback" in line.lower() or "synchronous" in line.lower():
            if "Synchronous fallback completed" in line or "attempting" in line:
                match = re.search(r"(\d+) bars", line)
                bars = int(match.group(1)) if match else 0
                metrics["fallbacks"].append({
                    "timestamp": line[:19],
                    "bars": bars,
                    "line": line.strip(),
                })
                print(f"⚠️  FALLBACK: {bars} bars retrieved via sync method")
        
        # Errors
        if "ERROR" in line or "FAILED" in line or "TIMEOUT" in line or "exception" in line.lower():
            metrics["errors"].append({
                "timestamp": line[:19],
                "message": line.strip(),
            })
            print(f"🔴 ERROR: {line.strip()[:100]}")
    
    return metrics

def print_summary(metrics):
    """Print summary statistics."""
    
    print("\n" + "="*80)
    print("📊 SESSION METRICS SUMMARY")
    print("="*80)
    
    if not metrics["hist_requests"]:
        print("❌ No historical requests processed yet")
        return
    
    # Cycle metrics
    print(f"\n📍 CYCLES COMPLETED: {len(metrics['cycles'])}")
    if metrics["cycles"]:
        print(f"   First cycle: {metrics['cycles'][0]['timestamp']}")
        print(f"   Latest cycle: {metrics['cycles'][-1]['timestamp']}")
    
    # Contract qualification
    print(f"\n📋 CONTRACTS QUALIFIED: {len(metrics['contract_qualifications'])}")
    for cq in metrics["contract_qualifications"]:
        print(f"   • {cq['symbol']}: conId={cq['conId']}")
    
    # Historical data stats
    print(f"\n📈 HISTORICAL DATA REQUESTS: {len(metrics['hist_requests'])}")
    
    spy_reqs = [r for r in metrics["hist_requests"] if r["symbol"] == "SPY"]
    qqq_reqs = [r for r in metrics["hist_requests"] if r["symbol"] == "QQQ"]
    
    if spy_reqs:
        avg_elapsed_spy = sum(r["elapsed"] for r in spy_reqs) / len(spy_reqs)
        avg_bars_spy = sum(r["bars"] for r in spy_reqs) / len(spy_reqs)
        print(f"\n   SPY: {len(spy_reqs)} requests")
        print(f"      • Avg elapsed: {avg_elapsed_spy:.2f}s (target: <30s) {'✅' if avg_elapsed_spy < 30 else '❌'}")
        print(f"      • Avg bars: {avg_bars_spy:.0f} (target: 60+) {'✅' if avg_bars_spy >= 60 else '❌'}")
        print(f"      • Success rate: {sum(1 for r in spy_reqs if r['bars'] > 0)}/{len(spy_reqs)} ✅")
    
    if qqq_reqs:
        avg_elapsed_qqq = sum(r["elapsed"] for r in qqq_reqs) / len(qqq_reqs)
        avg_bars_qqq = sum(r["bars"] for r in qqq_reqs) / len(qqq_reqs)
        print(f"\n   QQQ: {len(qqq_reqs)} requests")
        print(f"      • Avg elapsed: {avg_elapsed_qqq:.2f}s (target: <30s) {'✅' if avg_elapsed_qqq < 30 else '❌'}")
        print(f"      • Avg bars: {avg_bars_qqq:.0f} (target: 60+) {'✅' if avg_bars_qqq >= 60 else '❌'}")
        print(f"      • Success rate: {sum(1 for r in qqq_reqs if r['bars'] > 0)}/{len(qqq_reqs)} ✅")
    
    # Fallback usage
    if metrics["fallbacks"]:
        print(f"\n⚠️  FALLBACK USAGE: {len(metrics['fallbacks'])} events")
        fallback_rate = len(metrics["fallbacks"]) / len(metrics["hist_requests"]) * 100 if metrics["hist_requests"] else 0
        print(f"   Frequency: {fallback_rate:.1f}% (target: <10%)")
    else:
        print(f"\n✅ FALLBACK USAGE: 0 events (direct success)")
    
    # Errors
    if metrics["errors"]:
        print(f"\n🔴 ERRORS DETECTED: {len(metrics['errors'])}")
        for err in metrics["errors"][:3]:
            print(f"   • {err['timestamp']}: {err['message'][:100]}")
        if len(metrics["errors"]) > 3:
            print(f"   ... and {len(metrics['errors']) - 3} more")
    else:
        print(f"\n✅ ERRORS: None detected")
    
    print("\n" + "="*80)

def main():
    log_file = Path("logs/bot.log")
    
    print("🔍 Log Analysis Tool for IBKR Options Bot")
    print(f"📁 Monitoring: {log_file}")
    print(f"⏱️  Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    print("Press Ctrl+C to stop and show summary\n")
    
    try:
        while True:
            metrics = parse_log_file(log_file)
            
            # Show summary every 30 seconds or on demand
            import time
            time.sleep(2)  # Check every 2 seconds
            
    except KeyboardInterrupt:
        print("\n\n⏹️  Analysis stopped")
        metrics = parse_log_file(log_file)
        print_summary(metrics)
        
        # Determine scenario
        if metrics["hist_requests"]:
            successful = sum(1 for r in metrics["hist_requests"] if r["bars"] > 0)
            total = len(metrics["hist_requests"])
            success_rate = successful / total * 100 if total > 0 else 0
            
            if success_rate == 100 and not metrics["fallbacks"]:
                print("\n🎯 SCENARIO: A (Direct Success)")
                print("   ✅ All requests returned bars")
                print("   ✅ No fallback usage")
                print("   ✅ Ready for extended validation")
            elif success_rate == 100 and metrics["fallbacks"]:
                print("\n🎯 SCENARIO: B (Fallback Success)")
                print(f"   ✅ Success rate: {success_rate:.0f}%")
                print(f"   ⚠️  Fallback used: {len(metrics['fallbacks'])} times")
                print("   ⚠️  Document frequency and investigate if >50%")
            else:
                print("\n🎯 SCENARIO: C (Failure)")
                print(f"   ❌ Success rate: {success_rate:.0f}%")
                print("   ❌ Requires troubleshooting")

if __name__ == "__main__":
    main()
