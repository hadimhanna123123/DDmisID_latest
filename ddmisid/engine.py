"""Build the engine config and run the Snakemake backend pipeline."""

from pydantic import ValidationError  # Correct the typo
from .pydantic_config_model import DDmisIDConfig
import subprocess
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
    """Wrapper for running the Snakemake pipeline with dynamic flags."""
    try:
        cmd = ["snakemake"] + list(snakemake_args)
        logger.info(f"Running Snakemake with command: {' '.join(cmd)}") 
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        raise