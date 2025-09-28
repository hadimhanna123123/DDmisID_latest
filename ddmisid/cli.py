"""Command-line interface to build the DDmisID engine"""

import click
import os
from .engine import _run_snakemake, _load_config, get_config, _load_validated_config
from ddmisid.auth import kinit, oidc_device_login, oidc_export_env, ACCESS_TOKEN
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


def ensure_cern_oidc_auth():
    """Ensure CERN OIDC authentication is available.
    
    This function checks if a valid OIDC token exists and if not,
    initiates the device flow authentication.
    """
    # Use the standard CERN client ID that most tools use
    CLIENT_ID = "ddmisid"  # Registered client ID at https://application-portal.web.cern.ch/

   
    # # Check if we already have a valid token
    # if ACCESS_TOKEN.exists():
    #     logger.info("OIDC token found, exporting to environment")
    #     oidc_export_env("CERN_OIDC_TOKEN")
        
    #     # Debug: Print environment variable status
    #     logger.info(f"CERN_OIDC_TOKEN set: {'CERN_OIDC_TOKEN' in os.environ}")
    #     if "CERN_OIDC_TOKEN" in os.environ:
    #         token_preview = os.environ["CERN_OIDC_TOKEN"][:20] + "..." if len(os.environ["CERN_OIDC_TOKEN"]) > 20 else os.environ["CERN_OIDC_TOKEN"]
    #         logger.info(f"Token preview: {token_preview}")
        
    #     return
    
    # No token found, start device flow
    logger.info("OIDC authentication required - starting device flow")
    try:
        oidc_device_login(CLIENT_ID, verbose=True)
        oidc_export_env("CERN_OIDC_TOKEN")
        logger.info("OIDC authentication completed successfully")
    except Exception as e:
        logger.error(f"OIDC authentication failed: {e}")
        raise


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
        ddmisid-engine run -- --cores 4 --dry-run
    """
    # Step 1: Ensure CERN OIDC authentication
    ensure_cern_oidc_auth()
    
    # Step 2: Load config and initialize Kerberos
    try:
        _load_validated_config()
    except FileNotFoundError:
        logger.error("Config not set. Please build the DDmisID engine first with 'ddmisid-engine build'.")
        return
    
    config = get_config()

    kinit(config.user_id)
    
    # Step 3: Run Snakemake pipeline
    logger.info(f"Running the Snakemake pipeline with arguments: {snakemake_args}")
    
    try:
        _run_snakemake(snakemake_args)
    except Exception as e:
        logger.error(f"Snakemake execution failed: {e}")
    else:
        logger.info("Success: DDmisID engine run complete.")


@cli.command()
def test_auth_monitor():
    """Test the authentication monitoring system."""
    logger.info("Testing authentication monitoring system...")
    
    try:
        from .auth_monitor import create_monitoring_context, AuthPatternDetector
        from pathlib import Path
        import tempfile
        import time
        
        # Create a temporary log file with authentication prompts
        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
            test_log_path = Path(f.name)
            f.write("Starting test process...\n")
        
        # Test pattern detection
        detector = AuthPatternDetector()
        test_content = """
        CERN SINGLE SIGN-ON
        On your tablet, phone or computer, go to:
        https://auth.cern.ch/auth/realms/cern/device
        and enter the following code:
        TEST-1234
        You may also open the following link directly and follow the instructions:
        https://auth.cern.ch/auth/realms/cern/device?user_code=TEST-1234
        """
        
        detection = detector.detect_oidc_prompt(test_content)
        if detection:
            logger.success("✅ Pattern detection working correctly")
            logger.info(f"Detected patterns: {list(detection.keys())}")
            if 'extracted_code' in detection:
                logger.info(f"Extracted device code: {detection['extracted_code']}")
        else:
            logger.error("❌ Pattern detection failed")
            return
        
        # Test file monitoring
        logger.info("Testing file monitoring...")
        with create_monitoring_context() as monitor:
            monitor.start_monitoring([], [test_log_path])
            
            # Append authentication prompt to the file
            with open(test_log_path, 'a') as f:
                f.write("\n" + test_content)
            
            # Give the monitor time to detect the change
            time.sleep(2)
        
        # Cleanup
        test_log_path.unlink()
        logger.success("✅ Authentication monitoring test completed successfully")
        
    except ImportError as e:
        logger.error(f"❌ Authentication monitoring not available: {e}")
        logger.info("Install dependencies with: pip install watchdog")
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")


if __name__ == "__main__":
    cli()
