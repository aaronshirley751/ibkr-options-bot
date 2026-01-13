import subprocess
import time
import sys
import os

def run_verification():
    log_file = "logs/live_verification_20260113.log"
    print(f"Verifying LIVE configuration, logging to {log_file}...")
    
    os.makedirs("logs", exist_ok=True)
    
    with open(log_file, "w") as f:
        proc = subprocess.Popen(
            [sys.executable, "-m", "src.bot.app"], 
            stdout=f, 
            stderr=subprocess.STDOUT,
            cwd=os.getcwd(),
            env=os.environ.copy()
        )
    
    print(f"Bot started (PID: {proc.pid}). Checking startup for 15 seconds...")
    time.sleep(15)
    
    if proc.poll() is None:
        print("Bot is running successfully. Terminating verification process...")
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except:
            proc.kill()
    else:
        print(f"Bot exited early with code {proc.returncode}.")

if __name__ == "__main__":
    run_verification()
