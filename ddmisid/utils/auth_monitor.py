"""Authentication monitoring utilities for subprocess execution."""

import re
import subprocess
import threading
import time
from typing import Optional, Callable
from loguru import logger


class AuthenticationMonitor:
    """Monitor subprocess output for authentication prompts and handle them."""
    
    # Regex patterns to detect CERN authentication prompts
    AUTH_PATTERNS = [
        r"CERN SINGLE SIGN-ON",
        r"On your tablet, phone or computer, go to:",
        r"https://auth\.cern\.ch/auth/realms/cern/device",
        r"and enter the following code:",
        r"You may also open the following link directly",
        r"device\?user_code=",
        r"Please complete authentication in your browser",
        r"Waiting for authentication",
        r"Authentication required"
    ]
    
    def __init__(self):
        self.auth_detected = False
        self.auth_completed = False
        self.waiting_for_auth = False
        
    def is_auth_prompt(self, line: str) -> bool:
        """Check if a line contains an authentication prompt."""
        for pattern in self.AUTH_PATTERNS:
            if re.search(pattern, line, re.IGNORECASE):
                return True
        return False
    
    def wait_for_user_auth(self, timeout: int = 300) -> bool:
        """Wait for user to complete authentication."""
        if self.waiting_for_auth:
            return True  # Already waiting
            
        self.waiting_for_auth = True
        logger.info("🔐 AUTHENTICATION REQUIRED")
        logger.info("Please complete the authentication in your browser as shown above.")
        logger.info("Press ENTER when you have completed authentication to continue...")
        
        try:
            # Wait for user to press enter or timeout
            import select
            import sys
            
            # For Windows compatibility
            if sys.platform == "win32":
                input("Press ENTER when authentication is complete...")
            else:
                # Unix-like systems can use select for timeout
                i, _, _ = select.select([sys.stdin], [], [], timeout)
                if i:
                    input()
                else:
                    logger.error(f"Authentication timeout after {timeout} seconds")
                    return False
                    
            logger.info("✅ Continuing execution after authentication...")
            self.auth_completed = True
            self.waiting_for_auth = False
            return True
            
        except KeyboardInterrupt:
            logger.info("❌ Authentication cancelled by user")
            return False
        except Exception as e:
            logger.error(f"Error waiting for authentication: {e}")
            return False


def run_with_auth_monitoring(
    cmd: list, 
    cwd: Optional[str] = None, 
    timeout: int = 3600,
    auth_timeout: int = 300
) -> subprocess.CompletedProcess:
    """
    Run a subprocess with authentication monitoring.
    
    Args:
        cmd: Command to run as list
        cwd: Working directory
        timeout: Overall command timeout
        auth_timeout: Timeout for authentication wait
        
    Returns:
        CompletedProcess result
    """
    monitor = AuthenticationMonitor()
    
    logger.info(f"Running command with auth monitoring: {' '.join(cmd)}")
    
    # Start the process
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,  # Combine stderr with stdout
        text=True,
        bufsize=1,
        universal_newlines=True,
        cwd=cwd
    )
    
    output_lines = []
    auth_context_lines = []
    
    try:
        # Monitor output line by line
        while True:
            line = process.stdout.readline()
            if not line:
                # Check if process has finished
                if process.poll() is not None:
                    break
                continue
                
            line = line.rstrip('\n\r')
            output_lines.append(line)
            
            # Print the line immediately (real-time output)
            print(line)
            
            # Check for authentication prompts
            if monitor.is_auth_prompt(line):
                auth_context_lines.append(line)
                
                # If we detect the start of auth flow, collect more context
                if not monitor.auth_detected:
                    monitor.auth_detected = True
                    logger.info("🔍 Authentication prompt detected")
                    
                    # Wait a bit to collect the full auth prompt
                    time.sleep(2)
                    
                    # Pause execution and wait for user
                    if not monitor.wait_for_user_auth(auth_timeout):
                        logger.error("Authentication failed or timed out")
                        process.terminate()
                        raise RuntimeError("Authentication required but not completed")
                    
                    # Reset detection for potential future auth prompts
                    monitor.auth_detected = False
        
        # Wait for process to complete
        return_code = process.wait(timeout=timeout)
        
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=return_code,
            stdout='\n'.join(output_lines),
            stderr=None
        )
        
    except subprocess.TimeoutExpired:
        logger.error(f"Command timed out after {timeout} seconds")
        process.terminate()
        raise
    except KeyboardInterrupt:
        logger.info("Command interrupted by user")
        process.terminate()
        raise
    finally:
        # Ensure process is cleaned up
        if process.poll() is None:
            process.terminate()


def run_shell_with_auth_monitoring(
    script_path: str,
    cwd: Optional[str] = None,
    timeout: int = 3600,
    auth_timeout: int = 300
) -> subprocess.CompletedProcess:
    """
    Run a shell script with authentication monitoring.
    
    Args:
        script_path: Path to the shell script
        cwd: Working directory
        timeout: Overall script timeout
        auth_timeout: Timeout for authentication wait
        
    Returns:
        CompletedProcess result
    """
    cmd = ["bash", script_path]
    return run_with_auth_monitoring(cmd, cwd, timeout, auth_timeout)