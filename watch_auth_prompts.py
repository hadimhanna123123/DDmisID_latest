#!/usr/bin/env python3
"""
Standalone authentication prompt monitor for DDmisID.

Run this in a separate terminal while your main DDmisID workflow is running.
It will watch log files and display authentication prompts without interfering 
with your main processes.

Usage:
    python watch_auth_prompts.py                    # Monitor default log directories
    python watch_auth_prompts.py /path/to/logs     # Monitor specific directory
"""

import sys
import time
import re
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


class AuthPromptWatcher(FileSystemEventHandler):
    """Watches log files and displays authentication prompts."""
    
    def __init__(self):
        self.file_positions = {}
        self.shown_codes = set()
        
        # Simple patterns to detect OIDC prompts
        self.patterns = {
            'sso': re.compile(r'CERN SINGLE SIGN-ON', re.IGNORECASE),
            'code': re.compile(r'([A-Z0-9]{4}-[A-Z0-9]{4})', re.MULTILINE),
            'device_url': re.compile(r'device\?user_code=([A-Z0-9\-]+)', re.IGNORECASE),
        }
    
    def on_modified(self, event):
        """Check modified files for authentication prompts."""
        if event.is_directory:
            return
            
        filepath = Path(event.src_path)
        if not (filepath.suffix in ['.log', '.txt'] or 'log' in filepath.name.lower()):
            return
            
        self.check_file(filepath)
    
    def check_file(self, filepath):
        """Check a file for new authentication prompts."""
        try:
            if not filepath.exists():
                return
                
            filepath_str = str(filepath)
            
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                # Go to last known position
                last_pos = self.file_positions.get(filepath_str, 0)
                f.seek(last_pos)
                
                # Read new content
                new_content = f.read()
                if not new_content:
                    return
                    
                # Update position
                self.file_positions[filepath_str] = f.tell()
                
                # Look for authentication prompts
                if self.patterns['sso'].search(new_content):
                    device_code = self.extract_device_code(new_content)
                    if device_code and device_code not in self.shown_codes:
                        self.shown_codes.add(device_code)
                        self.display_prompt(filepath.name, device_code)
                        
        except Exception:
            # Silently handle file access errors
            pass
    
    def extract_device_code(self, text):
        """Extract device code from authentication prompt."""
        # Try URL parameter first
        match = self.patterns['device_url'].search(text)
        if match:
            return match.group(1)
        
        # Try standalone code pattern
        match = self.patterns['code'].search(text)
        if match:
            return match.group(1)
            
        return None
    
    def display_prompt(self, filename, device_code):
        """Display the authentication prompt."""
        timestamp = time.strftime("%H:%M:%S")
        
        print(f"\n{'='*80}")
        print(f"🔐 AUTHENTICATION REQUIRED at {timestamp}")
        print(f"📄 Detected in: {filename}")
        print(f"{'='*80}")
        print(f"📱 Go to: https://auth.cern.ch/auth/realms/cern/device")
        print(f"🔑 Enter code: {device_code}")
        print(f"🔗 Direct link: https://auth.cern.ch/auth/realms/cern/device?user_code={device_code}")
        print(f"{'='*80}")
        print(f"⏳ Process will continue after you authenticate in browser...")
        print(f"{'='*80}\n")


def main():
    """Main monitoring function."""
    print("🔐 DDmisID Authentication Prompt Monitor")
    print("=" * 50)
    print("This will watch for authentication prompts in log files.")
    print("Run this in a separate terminal while your DDmisID workflow runs.")
    print("Press Ctrl+C to stop monitoring.\n")
    
    # Determine directories to monitor
    if len(sys.argv) > 1:
        monitor_dirs = [Path(sys.argv[1])]
    else:
        # Default directories
        monitor_dirs = [
            Path("logs"),
            Path("workflow/logs"),
            Path(".snakemake/log"),
        ]
    
    # Check which directories exist
    existing_dirs = [d for d in monitor_dirs if d.exists()]
    
    if not existing_dirs:
        print("❌ No log directories found to monitor.")
        print("Make sure you're in the DDmisID project directory.")
        print("Or specify a directory: python watch_auth_prompts.py /path/to/logs")
        return 1
    
    print("📁 Monitoring directories:")
    for d in existing_dirs:
        print(f"   - {d.absolute()}")
    print()
    
    # Set up monitoring
    event_handler = AuthPromptWatcher()
    observer = Observer()
    
    for directory in existing_dirs:
        observer.schedule(event_handler, str(directory), recursive=True)
    
    observer.start()
    print("✅ Monitoring started. Watching for authentication prompts...")
    print("   (This will not interfere with your main workflow)")
    print()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n⏹️  Stopping monitor...")
        observer.stop()
    
    observer.join()
    print("✅ Monitor stopped.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except ImportError as e:
        print(f"❌ Error: Missing dependency - {e}")
        print("Install with: pip install watchdog")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)