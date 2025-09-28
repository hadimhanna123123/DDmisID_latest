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
# Global variable to store the validated config
config = None
config_path_json = Path(
    ".schema/validated_config.json"
)  # Hidden directory for the validated config
# book directory structure, if missing
config_path_json.parent.mkdir(parents=True, exist_ok=True)


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
    """Wrapper for running the Snakemake pipeline with dynamic flags and authentication prompt display."""
    try:
        # Import the monitoring system
        from .auth_monitor import monitor_snakemake_logs
        
        # Use the monitoring wrapper to display auth prompts from log files
        logger.info("🔍 Starting Snakemake with authentication prompt monitoring...")
        monitor_snakemake_logs(list(snakemake_args))
        
    except ImportError as e:
        # Fallback to original method if monitoring is not available
        logger.warning(f"Authentication monitoring not available, falling back to standard execution: {e}")
        cmd = ["snakemake"] + list(snakemake_args)
        logger.info(f"Running Snakemake with command: {' '.join(cmd)}")
        
        # Create environment with current environment plus ensure OIDC token is passed
        env = os.environ.copy()
        
        # Ensure OIDC token is in environment for subprocesses
        if "CERN_OIDC_TOKEN" not in env:
            logger.warning("CERN_OIDC_TOKEN not found in environment, subprocesses may need to authenticate")
        else:
            logger.info("CERN_OIDC_TOKEN found in environment, passing to Snakemake subprocesses")
        
        subprocess.run(cmd, check=True, env=env)
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