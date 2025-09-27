"""Build the engine config and run the Snakemake backend pipeline."""

from pydantic import ValidationError  # Correct the typo
from .pydantic_config_model import DDmisIDConfig
import subprocess
import os
from loguru import logger
from tabulate import tabulate
from pathlib import Path
import json
from ddmisid import read_config
import sys
import threading
import queue
import re
# Global variable to store the validated config
config = None
config_path_json = Path(
    ".schema/validated_config.json"
)  # Hidden directory for the validated config
# book directory structure, if missing
config_path_json.parent.mkdir(parents=True, exist_ok=True)


def handle_detected_authentication():
    """Helper function to handle authentication when detected in subprocess output."""
    from .auth import oidc_device_login, oidc_export_env
    
    print("\n" + "="*60)
    print("🔐 AUTHENTICATION HANDLER 🔐")
    print("It appears that authentication is required.")
    print("Would you like to authenticate now? (y/n)")
    
    response = input("Enter choice: ").strip().lower()
    if response in ['y', 'yes']:
        try:
            print("Starting CERN OIDC authentication...")
            oidc_device_login("ddmisid", verbose=True)
            oidc_export_env("CERN_OIDC_TOKEN")
            print("✅ Authentication completed successfully!")
            print("You can now re-run your command.")
        except Exception as e:
            print(f"❌ Authentication failed: {e}")
    else:
        print("Authentication skipped. You may need to authenticate manually.")
    print("="*60 + "\n")


def _load_config(config_path: str):
    """Load and validate the configuration file."""
    global config

    # read in the YAML config file and validate
    config_data = read_config(config_path)
    config = DDmisIDConfig(**config_data)

    # Persist the validated config to a hidden .ddmisid/.../validated_config.json
    with config_path_json.open("w") as f:
        f.write(json.dumps(config.dict(), indent=4))


def get_config():
    """Return the current value of the config."""
    return config


def _load_validated_config():
    """Load the pre-validated configuration from the JSON file."""
    global config
    if not config_path_json.exists():
        logger.error(f"Run 'ddmisid-engine build' first.")
        raise FileNotFoundError(
            f"Config build missing. Run 'ddmisid-engine build' first."
        )

    with config_path_json.open("r") as f:
        config_data = json.load(f)
        config = DDmisIDConfig(**config_data)


def _run_snakemake(snakemake_args):
    """Wrapper for running the Snakemake pipeline with dynamic flags and authentication monitoring."""
    import threading
    import queue
    import re
    
    def monitor_output(process, output_queue, stream_name):
        """Monitor process output for authentication prompts."""
        auth_patterns = [
            r"CERN SINGLE SIGN-ON",
            r"On your tablet, phone or computer, go to:",
            r"https://auth\.cern\.ch/auth/realms/cern/device",
            r"and enter the following code:",
            r"You may also open the following link directly",
            r"device\?user_code=",
            r"Starting CERN OIDC device login",
            r"OIDC authentication required"
        ]
        
        while True:
            try:
                if stream_name == 'stdout':
                    line = process.stdout.readline()
                else:
                    line = process.stderr.readline()
                
                if not line:
                    break
                    
                line = line.decode('utf-8', errors='replace').strip()
                if line:
                    # Check if this line contains authentication information
                    is_auth_line = any(re.search(pattern, line, re.IGNORECASE) for pattern in auth_patterns)
                    
                    if is_auth_line:
                        # Surface authentication prompts to main terminal
                        print(f"\n🔐 AUTHENTICATION REQUIRED 🔐")
                        print(f"From {stream_name}: {line}")
                        print("-" * 50)
                        logger.info(f"Authentication prompt detected: {line}")
                    
                    # Also put in queue for logging
                    output_queue.put((stream_name, line, is_auth_line))
                    
            except Exception as e:
                logger.error(f"Error monitoring {stream_name}: {e}")
                break
    
    try:
        cmd = ["snakemake"] + list(snakemake_args)
        logger.info(f"Running Snakemake with command: {' '.join(cmd)}")
        
        # Create environment with current environment plus ensure OIDC token is passed
        env = os.environ.copy()
        
        # Ensure OIDC token is in environment for subprocesses
        if "CERN_OIDC_TOKEN" not in env:
            logger.warning("CERN_OIDC_TOKEN not found in environment, subprocesses may need to authenticate")
        else:
            logger.info("CERN_OIDC_TOKEN found in environment, passing to Snakemake subprocesses")
        
        # Start process with streaming output
        process = subprocess.Popen(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            env=env,
            bufsize=1,
            universal_newlines=False
        )
        
        # Create queues and threads for monitoring output
        output_queue = queue.Queue()
        
        stdout_thread = threading.Thread(
            target=monitor_output, 
            args=(process, output_queue, 'stdout')
        )
        stderr_thread = threading.Thread(
            target=monitor_output, 
            args=(process, output_queue, 'stderr')
        )
        
        stdout_thread.daemon = True
        stderr_thread.daemon = True
        stdout_thread.start()
        stderr_thread.start()
        
        # Wait for process to complete while monitoring output
        auth_detected = False
        while process.poll() is None:
            try:
                stream_name, line, is_auth = output_queue.get(timeout=0.1)
                if is_auth:
                    auth_detected = True
                # Log all output normally
                logger.info(f"Snakemake {stream_name}: {line}")
            except queue.Empty:
                continue
        
        # Get any remaining output
        while not output_queue.empty():
            try:
                stream_name, line, is_auth = output_queue.get_nowait()
                if is_auth:
                    auth_detected = True
                logger.info(f"Snakemake {stream_name}: {line}")
            except queue.Empty:
                break
        
        # Check return code
        return_code = process.wait()
        
        if auth_detected:
            print("\n" + "="*60)
            print("🚨 AUTHENTICATION WAS REQUIRED DURING EXECUTION 🚨")
            print("Please check the authentication prompts above and")
            print("complete the authentication process in your browser.")
            print("")
            print("After completing authentication, you have two options:")
            print("1. Run 'ddmisid-engine auth' to update your stored credentials")
            print("2. Or simply re-run your original command")
            print("")
            print("The authentication URL and code should be visible above.")
            print("="*60 + "\n")
        
        if return_code != 0:
            raise subprocess.CalledProcessError(return_code, cmd)
            
    except subprocess.CalledProcessError as e:
        # Check if this is a lock error
        if e.returncode == 1:
            # Try to get the error output to check if it's a lock issue
            try:
                # Run the command again to capture stderr
                result = subprocess.run(cmd, capture_output=True, text=True)
                if "Directory cannot be locked" in result.stderr or "LockException" in result.stderr:
                    logger.warning("Snakemake directory is locked. Attempting to unlock...")
                    
                    # Run snakemake --unlock
                    unlock_cmd = ["snakemake", "--unlock"]
                    logger.info(f"Running unlock command: {' '.join(unlock_cmd)}")
                    subprocess.run(unlock_cmd, check=True)
                    
                    # Retry the original command with environment
                    logger.info(f"Retrying Snakemake command: {' '.join(cmd)}")
                    env = os.environ.copy()
                    subprocess.run(cmd, check=True, env=env)
                    return
            except subprocess.CalledProcessError as unlock_error:
                logger.error(f"Failed to unlock or retry Snakemake: {unlock_error}")
                raise e
        
        # If it's not a lock error or unlock failed, re-raise the original error
        raise