import subprocess
import time
import re
import sys
import argparse
from pathlib import Path
import threading

def tail_log(log_file, patterns, process_running):
    """Tails a log file and prints lines matching patterns."""
    log_path = Path(log_file)

    # Wait for the log file to be created
    while not log_path.exists() and process_running():
        time.sleep(0.5)

    if not process_running():
        return

    try:
        with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
            while process_running():
                line = f.readline()
                if not line:
                    time.sleep(0.1)
                    continue
                
                for pattern in patterns:
                    if re.search(pattern, line):
                        # Print the auth message to the main terminal
                        print(line, end="", file=sys.stdout)
                        sys.stdout.flush()
                        break
    except FileNotFoundError:
        print(f"Log file {log_file} disappeared during monitoring.", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description="Run a command and monitor its log for auth prompts.")
    parser.add_argument("--log-file", required=True, help="Path to the log file to monitor.")
    parser.add_argument("command", nargs='+', help="The command to execute.")
    args = parser.parse_args()

    auth_patterns = [
        r"CERN SINGLE SIGN-ON",
        r"On your tablet, phone or computer, go to:",
        r"https://auth.cern.ch/auth/realms/cern/device",
        r"and enter the following code:",
        r"You may also open the following link directly",
        r"device\?user_code="
    ]

    # Run the command
    process = subprocess.Popen(args.command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='ignore')

    # Function to check if the process is still running
    def process_running():
        return process.poll() is None

    # Start the log monitoring in a separate thread
    monitor_thread = threading.Thread(target=tail_log, args=(args.log_file, auth_patterns, process_running))
    monitor_thread.daemon = True
    monitor_thread.start()

    # Wait for the process to complete
    process.wait()
    
    # Allow the monitor thread a moment to catch up
    monitor_thread.join(timeout=2)

    if process.returncode != 0:
        print(f"Command failed with exit code {process.returncode}", file=sys.stderr)
        sys.exit(process.returncode)

if __name__ == "__main__":
    main()
