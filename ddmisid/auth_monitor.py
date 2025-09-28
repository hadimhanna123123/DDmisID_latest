"""
Authentication monitoring system for DDmisID workflows.

This module provides real-time monitoring of log files to detect CERN OIDC 
authentication prompts from subprocess tools like PIDCalib2, and handles 
re-authentication automatically while keeping the main processes running.
"""

import os
import re
import time
import threading
import subprocess
from pathlib import Path
from typing import List, Dict, Callable, Optional
from loguru import logger
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from ddmisid.auth import oidc_device_login, oidc_export_env
import json


class AuthPatternDetector:
    """Detects authentication prompts using regex patterns."""
    
    # OIDC authentication patterns
    OIDC_PATTERNS = {
        'sso_header': re.compile(r'CERN SINGLE SIGN-ON', re.IGNORECASE),
        'device_instruction': re.compile(r'On your tablet, phone or computer, go to:', re.IGNORECASE),
        'device_url': re.compile(r'https://auth\.cern\.ch/auth/realms/cern/device', re.IGNORECASE),
        'code_instruction': re.compile(r'and enter the following code:', re.IGNORECASE),
        'user_code': re.compile(r'device\?user_code=([A-Z0-9\-]+)', re.IGNORECASE),
        'direct_link': re.compile(r'You may also open the following link directly', re.IGNORECASE),
    }
    
    # Kerberos authentication patterns
    KERBEROS_PATTERNS = {
        'kinit_prompt': re.compile(r'Password for .+@CERN\.CH:', re.IGNORECASE),
        'ticket_expired': re.compile(r'kinit.*expired', re.IGNORECASE),
        'auth_failed': re.compile(r'kinit.*failed', re.IGNORECASE),
    }
    
    def detect_oidc_prompt(self, text: str) -> Optional[Dict[str, str]]:
        """
        Detect OIDC authentication prompts and extract relevant information.
        
        Returns:
            Dict with detected patterns and extracted values, or None if no prompt detected.
        """
        detected = {}
        
        for pattern_name, pattern in self.OIDC_PATTERNS.items():
            match = pattern.search(text)
            if match:
                detected[pattern_name] = match.group(0)
                if pattern_name == 'user_code' and match.groups():
                    detected['extracted_code'] = match.group(1)
        
        # Return detection if we found at least the SSO header
        return detected if 'sso_header' in detected else None
    
    def detect_kerberos_prompt(self, text: str) -> Optional[Dict[str, str]]:
        """Detect Kerberos authentication prompts."""
        detected = {}
        
        for pattern_name, pattern in self.KERBEROS_PATTERNS.items():
            match = pattern.search(text)
            if match:
                detected[pattern_name] = match.group(0)
        
        return detected if detected else None


class LogFileMonitor(FileSystemEventHandler):
    """Monitors log files for authentication prompts."""
    
    def __init__(self, 
                 callback: Callable[[str, Dict], None],
                 patterns_detector: AuthPatternDetector):
        self.callback = callback
        self.detector = patterns_detector
        self.monitored_files = {}  # filepath -> file handle
        self.file_positions = {}   # filepath -> last read position
        
    def on_modified(self, event):
        """Called when a monitored file is modified."""
        if event.is_directory:
            return
            
        filepath = Path(event.src_path)
        if filepath.suffix in ['.log', '.txt'] or 'log' in filepath.name.lower():
            self._check_file_for_auth_prompts(filepath)
    
    def add_file(self, filepath: Path):
        """Add a specific file to monitor."""
        if filepath.exists():
            self.file_positions[str(filepath)] = 0
            logger.info(f"Added {filepath} to authentication monitoring")
    
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
                    oidc_detection = self.detector.detect_oidc_prompt(new_content)
                    if oidc_detection:
                        logger.warning(f"OIDC authentication prompt detected in {filepath}")
                        self.callback(filepath_str, {'type': 'oidc', 'details': oidc_detection})
                    
                    kerberos_detection = self.detector.detect_kerberos_prompt(new_content)
                    if kerberos_detection:
                        logger.warning(f"Kerberos authentication prompt detected in {filepath}")
                        self.callback(filepath_str, {'type': 'kerberos', 'details': kerberos_detection})
                        
        except Exception as e:
            logger.error(f"Error monitoring {filepath}: {e}")


class AuthMonitorManager:
    """Manages the authentication monitoring system."""
    
    def __init__(self, client_id: str = "ddmisid"):
        self.client_id = client_id
        self.detector = AuthPatternDetector()
        self.monitor = LogFileMonitor(self._handle_auth_prompt, self.detector)
        self.observer = Observer()
        self.is_monitoring = False
        self.auth_lock = threading.Lock()
        
    def start_monitoring(self, log_directories: List[Path], specific_files: List[Path] = None):
        """Start monitoring log directories and specific files."""
        if self.is_monitoring:
            logger.warning("Monitoring already active")
            return
            
        # Monitor directories
        for log_dir in log_directories:
            if log_dir.exists():
                self.observer.schedule(self.monitor, str(log_dir), recursive=True)
                logger.info(f"Started monitoring directory: {log_dir}")
            else:
                logger.warning(f"Log directory does not exist: {log_dir}")
        
        # Monitor specific files
        if specific_files:
            for filepath in specific_files:
                self.monitor.add_file(filepath)
        
        self.observer.start()
        self.is_monitoring = True
        logger.info("Authentication monitoring started")
    
    def stop_monitoring(self):
        """Stop the monitoring system."""
        if self.is_monitoring:
            self.observer.stop()
            self.observer.join()
            self.is_monitoring = False
            logger.info("Authentication monitoring stopped")
    
    def _handle_auth_prompt(self, filepath: str, detection: Dict):
        """Handle detected authentication prompts."""
        with self.auth_lock:
            if detection['type'] == 'oidc':
                self._handle_oidc_prompt(filepath, detection['details'])
            elif detection['type'] == 'kerberos':
                self._handle_kerberos_prompt(filepath, detection['details'])
    
    def _handle_oidc_prompt(self, filepath: str, details: Dict):
        """Handle OIDC authentication prompts."""
        logger.warning(f"🔐 OIDC authentication required (detected in {Path(filepath).name})")
        
        # Extract user code if available
        if 'extracted_code' in details:
            logger.info(f"📱 Device code detected: {details['extracted_code']}")
            print(f"\n{'='*60}")
            print(f"🔐 AUTHENTICATION REQUIRED")
            print(f"📱 Go to: https://auth.cern.ch/auth/realms/cern/device")
            print(f"🔑 Enter code: {details['extracted_code']}")
            print(f"{'='*60}\n")
        
        try:
            # Attempt automatic re-authentication
            logger.info("🔄 Attempting automatic OIDC re-authentication...")
            oidc_device_login(self.client_id, verbose=True)
            oidc_export_env("CERN_OIDC_TOKEN")
            logger.success("✅ OIDC re-authentication successful")
            
        except Exception as e:
            logger.error(f"❌ Automatic OIDC re-authentication failed: {e}")
            print(f"\n⚠️  MANUAL AUTHENTICATION REQUIRED")
            print(f"Please run: ddmisid-engine build --config-path <your-config>")
            print(f"Or manually authenticate using: auth-get-user-token -c {self.client_id}\n")
    
    def _handle_kerberos_prompt(self, filepath: str, details: Dict):
        """Handle Kerberos authentication prompts."""
        logger.warning(f"🎫 Kerberos authentication required (detected in {Path(filepath).name})")
        print(f"\n{'='*60}")
        print(f"🎫 KERBEROS AUTHENTICATION REQUIRED")
        print(f"Please run: kinit <username>@CERN.CH")
        print(f"{'='*60}\n")


def create_monitoring_context(client_id: str = "ddmisid"):
    """
    Create a context manager for authentication monitoring.
    
    Usage:
        with create_monitoring_context() as monitor:
            monitor.start_monitoring([Path("logs")])
            # Your workflow runs here
    """
    
    class MonitoringContext:
        def __init__(self, client_id: str):
            self.manager = AuthMonitorManager(client_id)
            
        def __enter__(self):
            return self.manager
            
        def __exit__(self, exc_type, exc_val, exc_tb):
            self.manager.stop_monitoring()
    
    return MonitoringContext(client_id)


# Utility functions for integration with existing DDmisID workflow
def monitor_snakemake_logs(snakemake_args: List[str], client_id: str = "ddmisid"):
    """
    Run Snakemake with authentication monitoring.
    
    This function wraps the Snakemake execution with real-time authentication 
    monitoring to handle subprocess authentication prompts.
    """
    log_dirs = [
        Path("logs"),
        Path("workflow/logs"), 
        Path(".snakemake/log")
    ]
    
    with create_monitoring_context(client_id) as monitor:
        # Start monitoring before running Snakemake
        monitor.start_monitoring(log_dirs)
        
        try:
            # Run Snakemake
            cmd = ["snakemake"] + snakemake_args
            logger.info(f"🚀 Running Snakemake with authentication monitoring: {' '.join(cmd)}")
            
            env = os.environ.copy()
            proc = subprocess.run(cmd, env=env, check=True)
            
            logger.success("✅ Snakemake completed successfully")
            return proc
            
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Snakemake failed with exit code {e.returncode}")
            raise
        except KeyboardInterrupt:
            logger.warning("⚠️  Snakemake interrupted by user")
            raise


if __name__ == "__main__":
    # Example usage
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        # Test the monitoring system
        test_log = Path("test_auth.log")
        test_log.write_text("""
        Starting some process...
        CERN SINGLE SIGN-ON
        On your tablet, phone or computer, go to:
        https://auth.cern.ch/auth/realms/cern/device
        and enter the following code:
        TLIF-MMHA
        You may also open the following link directly and follow the instructions:
        https://auth.cern.ch/auth/realms/cern/device?user_code=TLIF-MMHA
        """)
        
        with create_monitoring_context() as monitor:
            monitor.start_monitoring([], [test_log])
            time.sleep(2)  # Give it time to detect
            
        test_log.unlink()  # Cleanup
        logger.info("Test completed")
    else:
        print("DDmisID Authentication Monitor")
        print("Usage: python auth_monitor.py test")
