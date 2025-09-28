"""Authentication utilities"""

import os
import json
import subprocess
import getpass
from pathlib import Path
from loguru import logger
import time
def kinit(username: str) -> None:
    """Perform kinit for Kerberos authentication with the CERN domain."""
    # Ensure the username is in the format <user>@CERN.CH
    
    if not username.endswith("@CERN.CH"):
        username = f"{username}@CERN.CH"

    # Allow up to three authentication attempts
    attempts = 0
    while attempts < 3:
        # Prompt for the password securely
        password = getpass.getpass(
            prompt=f"Initialising Kerberos ticket. Please enter password for {username} (Attempt {attempts + 1}/3): "
        )

        try:
            # Use subprocess to run kinit and pass the password via stdin
            process = subprocess.Popen(
                ["kinit", "-r", "7d", username],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            stdout, stderr = process.communicate(
                input=password.encode()
            )  # Send password to kinit

            # Check if kinit was successful
            if process.returncode == 0:
                logger.info(
                    f"Authentication successful. Kerberos ticket initialised for user ID {username}."
                )
                return  # Exit function on success
            else:
                attempts += 1
                logger.error(f"Authentication failed: {stderr.decode().strip()}")

        except Exception as e:
            logger.error(f"Error during kinit: {e}")
            attempts += 1

    # If all attempts fail, raise an exception
    raise RuntimeError(
        f"Failed to authenticate after 3 attempts for user ID {username}."
    )


# ---------------------------
# CERN OIDC device flow
# ---------------------------
DEFAULT_TOKEN_DIR = Path.home() / ".cache" / "cern-oidc"
DEFAULT_TOKEN_DIR.mkdir(parents=True, exist_ok=True)
TOKEN_JSON = DEFAULT_TOKEN_DIR / "token.json"
ACCESS_TOKEN = DEFAULT_TOKEN_DIR / "access.token"
REFRESH_TOKEN = DEFAULT_TOKEN_DIR / "refresh.token"


def oidc_device_login(client_id: str, audience: str | None = None, verbose: bool = True) -> dict:
    """
    Starts CERN OIDC device-code flow using `auth-get-user-token`,
    prints the device URL+code to the terminal, and writes the full JSON response.
    
    Token files are stored with restricted permissions (600) for security.

    Returns the parsed token JSON (contains access_token, refresh_token, expires_in, etc.).
    """
    # Ensure token directory has secure permissions
    DEFAULT_TOKEN_DIR.chmod(0o700)  # drwx------
    cmd = [
        "auth-get-user-token",
        "-c", client_id,
        "-o", str(TOKEN_JSON),
    ]
    if audience:
        cmd += ["-a", audience]
    if verbose:
        cmd += ["-v"]  # prints the device URL + user_code to the terminal

    logger.info("Starting CERN OIDC device login (watch this terminal for the device code)...")
    # Stream output so the user sees the device code immediately
    proc = subprocess.run(cmd, check=True)

    # Load the full JSON (we did NOT use -x, so refresh_token is included)
    with open(TOKEN_JSON, "r") as f:
        token_json = json.load(f)

    # Persist convenient files
    with open(ACCESS_TOKEN, "w") as f:
        f.write(token_json["access_token"])
    with open(REFRESH_TOKEN, "w") as f:
        f.write(token_json["refresh_token"])

    logger.info("OIDC token acquired and saved.")
    return token_json


def oidc_export_env(var_name: str = "CERN_OIDC_TOKEN") -> None:
    """
    Loads the saved access token and exports it in the current process env.
    Downstream subprocesses inherit it. Exports to multiple common environment
    variable names to ensure compatibility with different tools.
    """
    if not ACCESS_TOKEN.exists():
        raise RuntimeError(f"Access token not found at {ACCESS_TOKEN}. Run oidc_device_login() first.")
    
    token = ACCESS_TOKEN.read_text().strip()
    
    # Export to multiple common environment variable names
    env_vars = [var_name, "CERN_OIDC_TOKEN", "TOKEN", "AUTH_TOKEN", "BEARER_TOKEN"]
    for env_var in env_vars:
        os.environ[env_var] = token
    
    logger.info(f"Exported OIDC access token to environment variables: {', '.join(env_vars)}")


def oidc_refresh_token(client_id: str) -> dict:
    """
    Refresh the access token using the saved refresh_token.
    Keeps TOKEN_JSON in sync and updates ACCESS_TOKEN.
    """
    if not REFRESH_TOKEN.exists():
        raise RuntimeError(f"Refresh token not found at {REFRESH_TOKEN}. Do a device login first.")
    refresh = REFRESH_TOKEN.read_text().strip()

    cmd = [
        "curl", "-s", "-X", "POST",
        "https://auth.cern.ch/auth/realms/cern/protocol/openid-connect/token",
        "-d", "grant_type=refresh_token",
        "-d", f"client_id={client_id}",
        "-d", f"refresh_token={refresh}",
    ]
    out = subprocess.check_output(cmd)
    token_json = json.loads(out)

    TOKEN_JSON.write_text(json.dumps(token_json, indent=2))
    ACCESS_TOKEN.write_text(token_json["access_token"])
    logger.info("OIDC access token refreshed.")
    return token_json