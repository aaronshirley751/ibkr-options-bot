import time
import re
import os

LOG_FILE = "logs/session_20260113_extended_2.log"

def tail_f(file_path):
    print(f"Monitoring {file_path}...")
    try:
        with open(file_path, "r") as f:
            # Go to the end of the file
            f.seek(0, 2)
            while True:
                line = f.readline()
                if not line:
                    time.sleep(0.5)
                    continue
                print(line.strip())
                # Highlight key events
                if "Cycle complete" in line:
                    print("-" * 50)
                if "ERROR" in line or "CRITICAL" in line:
                     print("!!! ERROR DETECTED !!!")
    except FileNotFoundError:
        print(f"File {file_path} not found yet.")
    except KeyboardInterrupt:
        print("\nMonitoring stopped.")

if __name__ == "__main__":
    if os.path.exists(LOG_FILE):
        tail_f(LOG_FILE)
    else:
        print(f"Waiting for {LOG_FILE} to be created...")
