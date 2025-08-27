"""Command-line interface to build the DDmisID engine"""

import click
from .engine import _run_snakemake, _load_config, get_config, _load_validated_config
from ddmisid.auth import kinit
from pydantic import ValidationError
from loguru import logger
from pathlib import Path
from .pydantic_config_model import DDmisIDConfig  # Import the model for validation
from tabulate import tabulate

# Setup logging
logdir = Path("logs/engine")
logdir.mkdir(parents=True, exist_ok=True)
logger.add(
    logdir / "ddmisid_log_{time}.log",
    rotation="1 day",
    retention="7 days",
    level="INFO",
)


@click.group()  # Add this to ensure cli group is registered
def cli():
    """Command-line interface to build the DDmisID engine"""
    pass


@cli.command()
@click.option(
    "-c",
    "--config-path",  # This is the CLI flag (external option for the user)
    help="Path to the YAML user-defined configuration file",
    default="config/main.yml",
    required=False,
)
def build(config_path):  # This is the corresponding Python variable for the option
    """Build the DDmisID configuration and objects.

    Example:
        ddmisid-engine build --config-path config/main.yml
    """
    logger.info(f"Building the DDmisID engine from: {config_path}")

    # Load and validate the configuration
    try:
        _load_config(config_path)  # Pass config_path to _load_config

        config = get_config()  # retrive updated global config
        if config is None:  # Ensure config is loaded correctly
            logger.error("Config not set. Please ensure the configuration is valid.")
            return
        logger.info(f"DDmisID engine built successfully from: {config_path}")

        # Print a detailed report of the full configuration
        config_report = config.model_dump_json(indent=4)
        logger.info(
            f"\n\nConfiguration report:\n---------------------\n{config_report}"
        )

    except ValidationError as e:
        logger.error(f"Validation failed for configuration: {e}")
    except Exception as e:
        logger.error(f"Failed to build DDmisID engine: {e}")


@cli.command()
@click.argument("snakemake_args", nargs=-1, type=click.UNPROCESSED)
def run(snakemake_args):
    """Run the Snakemake backend pipeline with dynamic flags.

    This command passes any Snakemake flag to the workflow.

    Example:
        ddmisid-engine run --cores 4 --dry-run
    """
    # initialise kerberos ticket to access EOS
    config = get_config()
    if config is None:
        logger.error("Config not set. Please build the DDmisID engine first.")
        return
    kinit(config.user_id)
    logger.info(f"Running the Snakemake pipeline with arguments: {snakemake_args}")

    # run the backend snakemake pipeline
    try:
        _run_snakemake(snakemake_args)
    except Exception as e:
        logger.error(f"Snakemake execution failed: {e}")
    else:
        logger.info("Success: DDmisID engine run complete.")


if __name__ == "__main__":
    cli()
