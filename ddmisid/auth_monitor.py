import subprocess
import re
import sys
import argparse
import threading
import time
import select
import os

def main():
    """
    Runs a command, writes its output to a log file, and simultaneously
    monitors the output for authentication patterns, printing them to the console.
    """
    parser = argparse.ArgumentParser(description="Run a command and monitor its log for auth prompts.")
    parser.add_argument("--log-file", required=True, help="Path to the log file to write.")
    parser.add_argument("--timeout", type=int, default=600, help="Timeout in seconds (default: 600)")
    parser.add_argument("command", nargs=argparse.REMAINDER, help="The command to execute.")
    args = parser.parse_args()

    if not args.command:
        print("Error: No command provided to execute.", file=sys.stderr)
        sys.exit(1)

    # Patterns to detect authentication issues
    auth_patterns = [
        re.compile(p, re.IGNORECASE) for p in [
            r"CERN SINGLE SIGN-ON",
            r"On your tablet, phone or computer, go to:",
            r"https://auth.cern.ch/auth/realms/cern/device",
            r"and enter the following code:",
            r"You may also open the following link directly",
            r"device\?user_code=",
            r"authentication.*required",
            r"token.*expired",
            r"unauthorized",
            r"access.*denied",
            r"login.*required"
        ]
    ]

    try:
        print(f"Starting command: {' '.join(args.command)}", file=sys.stderr)
        
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
            start_time = time.time()
            last_output_time = start_time
            
            # Read output line by line with timeout handling
            while True:
                # Check if process has finished
                if process.poll() is not None:
                    # Process finished, read any remaining output
                    remaining_output = process.stdout.read()
                    if remaining_output:
                        log_f.write(remaining_output)
                        log_f.flush()
                        # Check remaining output for auth patterns
                        for pattern in auth_patterns:
                            if pattern.search(remaining_output):
                                print(remaining_output, end="", file=sys.stdout)
                                sys.stdout.flush()
                                break
                    break
                
                # Check for timeout
                current_time = time.time()
                if current_time - last_output_time > args.timeout:
                    print(f"\n⚠️  WARNING: No output for {args.timeout} seconds. Process may be hanging.", file=sys.stderr)
                    print("This could indicate an authentication timeout or other issue.", file=sys.stderr)
                    print("Consider checking if your CERN token is still valid.", file=sys.stderr)
                    process.terminate()
                    time.sleep(5)
                    if process.poll() is None:
                        process.kill()
                    sys.exit(124)  # Timeout exit code
                
                # Try to read a line with a short timeout
                try:
                    # On Windows, we can't use select, so we'll use a different approach
                    if os.name == 'nt':  # Windows
                        line = process.stdout.readline()
                        if line:
                            last_output_time = current_time
                        else:
                            time.sleep(0.1)
                            continue
                    else:  # Unix-like systems
                        ready, _, _ = select.select([process.stdout], [], [], 1.0)
                        if ready:
                            line = process.stdout.readline()
                            if line:
                                last_output_time = current_time
                            else:
                                continue
                        else:
                            continue
                except:
                    # Fallback for any select issues
                    line = process.stdout.readline()
                    if line:
                        last_output_time = current_time
                    else:
                        time.sleep(0.1)
                        continue
                
                if not line:
                    continue
                    
                # Write every line to the log file
                log_f.write(line)
                log_f.flush()

                # Check if the line matches any auth pattern
                for pattern in auth_patterns:
                    if pattern.search(line):
                        # Print the auth message to the main terminal with highlighting
                        print(f"\n🔐 AUTHENTICATION REQUIRED:", file=sys.stdout)
                        print(line, end="", file=sys.stdout)
                        sys.stdout.flush()
                        break
                
                # Print progress indicator every 30 seconds of silence
                if current_time - last_output_time > 30 and (int(current_time - last_output_time) % 30 == 0):
                    print(f"⏳ Process running... ({int(current_time - start_time)}s elapsed)", file=sys.stderr)
        
        # Wait for the process to complete and get the return code
        process.wait()

        if process.returncode != 0:
            print(f"\n❌ Command failed with exit code {process.returncode}", file=sys.stderr)
            sys.exit(process.returncode)
        else:
            print(f"✅ Command completed successfully", file=sys.stderr)

    except FileNotFoundError:
        print(f"Error: Command not found: {args.command[0]}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
