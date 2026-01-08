#!/usr/bin/env python3
"""
Phase 3: Extended Dry-Run Monitoring (4+ Hours)
Monitors bot execution with live IBKR Gateway, capturing:
- Cycle completion times
- Buffer warnings detection
- Memory usage
- Error rates
- Market data validity
"""

import os
import sys
import time
import psutil
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Configuration
LOG_FILE = Path("logs/phase3_extended_run.log")
BOT_LOG = Path("logs/bot.log")
TARGET_DURATION_HOURS = 4
CHECK_INTERVAL_SECONDS = 60  # Check every minute
BUFFER_WARNING_PATTERN = "Output exceeded limit"

class Phase3Monitor:
    def __init__(self):
        self.start_time = time.time()
        self.target_duration = TARGET_DURATION_HOURS * 3600
        self.metrics = {
            "buffer_warnings": 0,
            "errors": 0,
            "cycles_detected": 0,
            "last_cycle_time": None,
            "peak_memory_mb": 0,
        }
        self.bot_process = None
        
    def find_bot_process(self):
        """Find the running bot process"""
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = proc.info.get('cmdline', [])
                if cmdline and 'src.bot.app' in ' '.join(cmdline):
                    return proc
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return None
    
    def check_buffer_warnings(self):
        """Check Gateway logs for buffer warnings"""
        # Note: Gateway logs not accessible from bot, but we can check bot logs for symptoms
        if BOT_LOG.exists():
            content = BOT_LOG.read_text()
            count = content.count("TimeoutError")
            count += content.count("connection failed")
            return count
        return 0
    
    def check_bot_log(self):
        """Parse bot log for metrics"""
        if not BOT_LOG.exists():
            return
        
        # Read last 1000 lines for recent activity
        with open(BOT_LOG, 'r') as f:
            lines = f.readlines()[-1000:]
        
        for line in lines:
            if "Cycle #" in line or "Cycle decision" in line:
                self.metrics["cycles_detected"] += 1
                self.metrics["last_cycle_time"] = datetime.now()
            if "ERROR" in line:
                self.metrics["errors"] += 1
    
    def get_memory_usage(self):
        """Get bot process memory usage"""
        if self.bot_process is None:
            self.bot_process = self.find_bot_process()
        
        if self.bot_process:
            try:
                mem_info = self.bot_process.memory_info()
                mem_mb = mem_info.rss / (1024 * 1024)
                if mem_mb > self.metrics["peak_memory_mb"]:
                    self.metrics["peak_memory_mb"] = mem_mb
                return mem_mb
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                self.bot_process = None
        return 0
    
    def log_metrics(self, elapsed_seconds):
        """Log current metrics"""
        elapsed_hours = elapsed_seconds / 3600
        remaining_hours = (self.target_duration - elapsed_seconds) / 3600
        mem_mb = self.get_memory_usage()
        
        status = f"""
╔═══════════════════════════════════════════════════════════════════╗
║ Phase 3 Extended Dry-Run Status
╚═══════════════════════════════════════════════════════════════════╝

Time:      {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Elapsed:   {elapsed_hours:.2f} hours ({elapsed_seconds/60:.0f} minutes)
Remaining: {remaining_hours:.2f} hours

Metrics:
  Cycles Detected:     {self.metrics['cycles_detected']}
  Last Cycle:          {self.metrics['last_cycle_time'] or 'N/A'}
  Buffer Warnings:     {self.metrics['buffer_warnings']}
  Errors:              {self.metrics['errors']}
  Current Memory:      {mem_mb:.1f} MB
  Peak Memory:         {self.metrics['peak_memory_mb']:.1f} MB

Bot Process:           {'✅ Running' if self.bot_process else '❌ Not Found'}

Target: {TARGET_DURATION_HOURS} hours | Check Interval: {CHECK_INTERVAL_SECONDS}s
"""
        
        print(status)
        
        # Append to log file
        with open(LOG_FILE, 'a') as f:
            f.write(f"\n{'-'*70}\n")
            f.write(f"[{datetime.now().isoformat()}] Phase 3 Status\n")
            f.write(f"Elapsed: {elapsed_hours:.2f}h | Cycles: {self.metrics['cycles_detected']} | ")
            f.write(f"Warnings: {self.metrics['buffer_warnings']} | Errors: {self.metrics['errors']} | ")
            f.write(f"Memory: {mem_mb:.1f}MB\n")
    
    def run(self):
        """Main monitoring loop"""
        LOG_FILE.parent.mkdir(exist_ok=True)
        
        print("=" * 70)
        print("PHASE 3: EXTENDED DRY-RUN MONITORING")
        print("=" * 70)
        print(f"Target Duration: {TARGET_DURATION_HOURS} hours")
        print(f"Check Interval: {CHECK_INTERVAL_SECONDS} seconds")
        print(f"Log File: {LOG_FILE}")
        print("=" * 70)
        print()
        
        with open(LOG_FILE, 'a') as f:
            f.write(f"\n{'='*70}\n")
            f.write(f"Phase 3 Extended Dry-Run Started: {datetime.now().isoformat()}\n")
            f.write(f"Target Duration: {TARGET_DURATION_HOURS} hours\n")
            f.write(f"{'='*70}\n")
        
        while True:
            elapsed = time.time() - self.start_time
            
            # Update metrics
            self.check_bot_log()
            self.metrics["buffer_warnings"] = self.check_buffer_warnings()
            
            # Log status
            self.log_metrics(elapsed)
            
            # Check if target duration reached
            if elapsed >= self.target_duration:
                print("\n" + "="*70)
                print("✅ TARGET DURATION REACHED")
                print("="*70)
                self.print_summary()
                break
            
            # Wait for next check
            time.sleep(CHECK_INTERVAL_SECONDS)
    
    def print_summary(self):
        """Print final summary"""
        elapsed_hours = (time.time() - self.start_time) / 3600
        
        summary = f"""
╔═══════════════════════════════════════════════════════════════════╗
║ PHASE 3 EXTENDED DRY-RUN COMPLETE
╚═══════════════════════════════════════════════════════════════════╝

Duration:        {elapsed_hours:.2f} hours
Total Cycles:    {self.metrics['cycles_detected']}
Buffer Warnings: {self.metrics['buffer_warnings']}
Errors:          {self.metrics['errors']}
Peak Memory:     {self.metrics['peak_memory_mb']:.1f} MB

SUCCESS CRITERIA:
  {'✅' if self.metrics['buffer_warnings'] == 0 else '❌'} Buffer Warnings = 0 (actual: {self.metrics['buffer_warnings']})
  {'✅' if self.metrics['cycles_detected'] >= 60 else '❌'} Cycles >= 60 (actual: {self.metrics['cycles_detected']})
  {'✅' if self.metrics['peak_memory_mb'] < 500 else '❌'} Peak Memory < 500MB (actual: {self.metrics['peak_memory_mb']:.1f})
  {'✅' if self.metrics['errors'] < 5 else '❌'} Errors < 5 (actual: {self.metrics['errors']})

Status: {'✅ PASSED' if self._is_success() else '❌ NEEDS REVIEW'}

Log File: {LOG_FILE}
Bot Log: {BOT_LOG}
"""
        
        print(summary)
        
        with open(LOG_FILE, 'a') as f:
            f.write(f"\n{'='*70}\n")
            f.write(f"Phase 3 Complete: {datetime.now().isoformat()}\n")
            f.write(f"Duration: {elapsed_hours:.2f}h | Cycles: {self.metrics['cycles_detected']}\n")
            f.write(f"Warnings: {self.metrics['buffer_warnings']} | Errors: {self.metrics['errors']}\n")
            f.write(f"Peak Memory: {self.metrics['peak_memory_mb']:.1f}MB\n")
            f.write(f"Status: {'PASSED' if self._is_success() else 'NEEDS REVIEW'}\n")
            f.write(f"{'='*70}\n")
    
    def _is_success(self):
        """Check if Phase 3 passed"""
        return (
            self.metrics['buffer_warnings'] == 0 and
            self.metrics['cycles_detected'] >= 60 and
            self.metrics['peak_memory_mb'] < 500 and
            self.metrics['errors'] < 5
        )

if __name__ == "__main__":
    monitor = Phase3Monitor()
    try:
        monitor.run()
    except KeyboardInterrupt:
        print("\n\n⚠️  Monitoring stopped by user")
        print("\nPartial results:")
        monitor.print_summary()
        sys.exit(1)
