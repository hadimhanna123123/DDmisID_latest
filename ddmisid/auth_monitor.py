"""
Simple authentication prompt display system for DDmisID workflows.

This module provides real-time monitoring of log files to detect CERN OIDC 
authentication prompts from subprocess tools like PIDCalib2, and displays 
them prominently in the main terminal so users don't have to hunt through 
log files to find authentication prompts.
"""

import re
import time
import threading
from pathlib import Path
from typing import List, Dict, Optional
from loguru import logger
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


class AuthPromptDetector:
    """Detects authentication prompts using regex patterns."""
    
    # OIDC authentication patterns - simplified to just detect the essential parts
    OIDC_PATTERNS = {
        'sso_header': re.compile(r'CERN SINGLE SIGN-ON', re.IGNORECASE),
        'device_url': re.compile(r'https://auth\.cern\.ch/auth/realms/cern/device', re.IGNORECASE),
        'user_code': re.compile(r'device\?user_code=([A-Z0-9\-]+)', re.IGNORECASE),
        'code_line': re.compile(r'^([A-Z0-9]{4}-[A-Z0-9]{4})$', re.MULTILINE),
    }
    
    def detect_auth_prompt(self, text: str) -> Optional[Dict[str, str]]:
        """
        Detect OIDC authentication prompts and extract the device code.
        
        Returns:
            Dict with device code and URL, or None if no prompt detected.
        """
        # Look for the SSO header first
        if not self.OIDC_PATTERNS['sso_header'].search(text):
            return None
        
        # Extract device code from URL parameter
        url_match = self.OIDC_PATTERNS['user_code'].search(text)
        if url_match:
            return {
                'device_code': url_match.group(1),
                'auth_url': f"https://auth.cern.ch/auth/realms/cern/device?user_code={url_match.group(1)}"
            }
        
        # Try to find code on its own line (like ZPXN-ZNKP)
        code_match = self.OIDC_PATTERNS['code_line'].search(text)
        if code_match:
            return {
                'device_code': code_match.group(1),
                'auth_url': f"https://auth.cern.ch/auth/realms/cern/device?user_code={code_match.group(1)}"
            }
        
        return None


class LogMonitor(FileSystemEventHandler):
    """Monitors log files for authentication prompts and displays them."""
    
    def __init__(self, display_callback):
        self.display_callback = display_callback
        self.detector = AuthPromptDetector()
        self.file_positions = {}   # filepath -> last read position
        self.displayed_codes = set()  # Track already displayed codes to avoid duplicates
        
    def on_modified(self, event):
        """Called when a monitored file is modified."""
        if event.is_directory:
            return
            
        filepath = Path(event.src_path)
        # Only monitor log files
        if filepath.suffix in ['.log', '.txt'] or 'log' in filepath.name.lower():
            self._check_file_for_auth_prompts(filepath)
    
    def _check_file_for_auth_prompts(self, filepath: Path):
        """Check a file for authentication prompts since last read."""
        filepath_str = str(filepath)
        
        try:
            if not filepath.exists():
                return
                
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                # Seek to last known position
                last_pos = self.file_positions.get(filepath_str, 0)
                f.seek(last_pos)
                
                # Read new content
                new_content = f.read()
                if new_content:
                    # Update position
                    self.file_positions[filepath_str] = f.tell()
                    
                    # Check for authentication prompts
                    auth_info = self.detector.detect_auth_prompt(new_content)
                    if auth_info:
                        # Avoid displaying the same code multiple times
                        code = auth_info['device_code']
                        if code not in self.displayed_codes:
                            self.displayed_codes.add(code)
                            self.display_callback(filepath.name, auth_info)
                        
        except Exception as e:
            # Silently handle file access errors (files might be locked during writing)
            pass


def display_auth_prompt(log_filename: str, auth_info: Dict[str, str]):
    """Display the authentication prompt prominently in the terminal."""
    device_code = auth_info['device_code']
    auth_url = auth_info['auth_url']
    
    print(f"\n{'='*70}")
    print(f"🔐 AUTHENTICATION REQUIRED (from {log_filename})")
    print(f"{'='*70}")
    print(f"📱 Go to: https://auth.cern.ch/auth/realms/cern/device")
    print(f"🔑 Enter code: {device_code}")
    print(f"🔗 Or click: {auth_url}")
    print(f"{'='*70}")
    print(f"⏳ Waiting for authentication... (process will continue automatically)")
    print(f"{'='*70}\n")


class AuthPromptMonitor:
    """Simple monitor that displays authentication prompts in the main terminal."""
    
    def __init__(self):
        self.monitor = LogMonitor(display_auth_prompt)
        self.observer = Observer()
        self.is_monitoring = False
        
    def start_monitoring(self, log_directories: List[Path]):
        """Start monitoring log directories for authentication prompts."""
        if self.is_monitoring:
            return
            
        # Monitor directories
        for log_dir in log_directories:
            if log_dir.exists():
                self.observer.schedule(self.monitor, str(log_dir), recursive=True)
                logger.info(f"Monitoring {log_dir} for authentication prompts")
            else:
                logger.warning(f"Log directory does not exist: {log_dir}")
        
        self.observer.start()
        self.is_monitoring = True
    
    def stop_monitoring(self):
        """Stop the monitoring system."""
        if self.is_monitoring:
            self.observer.stop()
            self.observer.join()
            self.is_monitoring = False


def monitor_snakemake_logs(snakemake_args: List[str]):
    """
    Run Snakemake with authentication prompt monitoring.
    
    This function wraps the Snakemake execution with real-time authentication 
    prompt detection to display them in the main terminal.
    """
    import subprocess
    import os
    
    # Common log directories created by Snakemake and DDmisID
    log_dirs = [
        Path("logs"),
        Path("workflow/logs"), 
        Path(".snakemake/log")
    ]
    
    monitor = AuthPromptMonitor()
    
    try:
        # Start monitoring before running Snakemake
        monitor.start_monitoring(log_dirs)
        logger.info("� Started monitoring log files for authentication prompts")
        
        # Run Snakemake
        cmd = ["snakemake"] + snakemake_args
        logger.info(f"Running Snakemake: {' '.join(cmd)}")
        
        env = os.environ.copy()
        proc = subprocess.run(cmd, env=env, check=True)
        
        logger.info("✅ Snakemake completed successfully")
        return proc
        
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Snakemake failed with exit code {e.returncode}")
        raise
    except KeyboardInterrupt:
        logger.warning("⚠️  Snakemake interrupted by user")
        raise
    finally:
        monitor.stop_monitoring()


# Simple context manager for manual use
class AuthMonitorContext:
    """Context manager for authentication monitoring."""
    
    def __init__(self):
        self.monitor = AuthPromptMonitor()
        
    def __enter__(self):
        return self.monitor
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.monitor.stop_monitoring()


def create_auth_monitor():
    """Create a context manager for authentication monitoring."""
    return AuthMonitorContext()


if __name__ == "__main__":
    # Simple test
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        # Test the detection
        test_log = Path("test_auth.log")
        test_log.write_text("""
        Starting some process...
        CERN SINGLE SIGN-ON
        On your tablet, phone or computer, go to:
        https://auth.cern.ch/auth/realms/cern/device
        and enter the following code:
        TEST-1234
        You may also open the following link directly:
        https://auth.cern.ch/auth/realms/cern/device?user_code=TEST-1234
        """)
        
        with create_auth_monitor() as monitor:
            monitor.start_monitoring([test_log.parent])
            time.sleep(2)  # Give it time to detect
            
        test_log.unlink()  # Cleanup
        print("Test completed")
    else:
        print("DDmisID Authentication Prompt Monitor")
        print("Usage: python auth_monitor.py test")
