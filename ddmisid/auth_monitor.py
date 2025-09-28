import subprocess
import re
import sys
import argparse
import threading

def main():
    """
    Runs a command, writes its output to a log file, and simultaneously
    monitors the output for authentication patterns, printing them to the console.
    """
    parser = argparse.ArgumentParser(description="Run a command and monitor its log for auth prompts.")
    parser.add_argument("--log-file", required=True, help="Path to the log file to write.")
    parser.add_argument("command", nargs=argparse.REMAINDER, help="The command to execute.")
    args = parser.parse_args()

    if not args.command:
        print("Error: No command provided to execute.", file=sys.stderr)
        sys.exit(1)

    auth_patterns = [
        re.compile(p) for p in [
            r"CERN SINGLE SIGN-ON",
            r"On your tablet, phone or computer, go to:",
            r"https://auth.cern.ch/auth/realms/cern/device",
            r"and enter the following code:",
            r"You may also open the following link directly",
            r"device\?user_code="
        ]
    ]

    try:
        # Start the subprocess, capturing its stdout and stderr
        process = subprocess.Popen(
            args.command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            errors='ignore',
            bufsize=1  # Line-buffered
        )

        # Open the log file for writing
        with open(args.log_file, "w", encoding='utf-8') as log_f:
            # Read output line by line in real-time
            for line in iter(process.stdout.readline, ''):
                # Write every line to the log file
                log_f.write(line)
                log_f.flush()

                # Check if the line matches any auth pattern
                for pattern in auth_patterns:
                    if pattern.search(line):
                        # Print the auth message to the main terminal
                        print(line, end="", file=sys.stdout)
                        sys.stdout.flush()
                        break
        
        # Wait for the process to complete and get the return code
        process.wait()

        if process.returncode != 0:
            print(f"\nCommand failed with exit code {process.returncode}", file=sys.stderr)
            sys.exit(process.returncode)

    except FileNotFoundError:
        print(f"Error: Command not found: {args.command[0]}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
