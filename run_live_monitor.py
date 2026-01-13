import subprocess
import sys
import os
import time

def start_bot():
    log_file = "logs/session_production_monitoring.log"
    print(f"Launching production bot, logging to {log_file}...")
    
    # Ensure logs directory exists
    os.makedirs("logs", exist_ok=True)
    
    # Open log file for writing
    f = open(log_file, "w")
    
    # Launch independently
    # shell=True helps detach in some environments, or just Popen
    proc = subprocess.Popen(
        [sys.executable, "-m", "src.bot.app"], 
        stdout=f, 
        stderr=subprocess.STDOUT,
        cwd=os.getcwd(),
        env=os.environ.copy()
    )
    
    print(f"Bot started with PID {proc.pid}.")
    print("Monitor script exiting, bot should continue running.")
    # We do NOT wait for proc.

if __name__ == "__main__":
    start_bot()
