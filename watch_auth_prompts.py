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
    
    def __init__(self, observer):
        self.file_positions = {}
        self.shown_codes = set()
        self.observer = observer
        self.monitored_dirs = set()
        
        # Enhanced patterns to detect various authentication prompts
        self.patterns = {
            'sso': re.compile(r'CERN SINGLE SIGN-ON|Please go to|device\?user_code|auth\.cern\.ch', re.IGNORECASE),
            'code': re.compile(r'([A-Z0-9]{4}-[A-Z0-9]{4})', re.MULTILINE),
            'device_url': re.compile(r'device\?user_code=([A-Z0-9\-]+)', re.IGNORECASE),
            'auth_url': re.compile(r'https://auth\.cern\.ch[^\s]*', re.IGNORECASE),
            'oidc_flow': re.compile(r'Starting CERN OIDC device login|watch this terminal for the device code', re.IGNORECASE),
            'token_required': re.compile(r'OIDC authentication required|CERN_OIDC_TOKEN not found', re.IGNORECASE),
        }
    
    def on_created(self, event):
        """Handle creation of new files and directories."""
        if event.is_directory:
            # New directory created - start monitoring if it looks like a log directory
            dir_path = Path(event.src_path)
            if self.should_monitor_directory(dir_path):
                self.add_directory_monitoring(dir_path)
        else:
            # New file created - check if it's a log file
            filepath = Path(event.src_path)
            if self.is_log_file(filepath):
                print(f"📁 New log file detected: {filepath}")
                self.check_file(filepath)
    
    def on_modified(self, event):
        """Check modified files for authentication prompts."""
        if event.is_directory:
            return
            
        filepath = Path(event.src_path)
        if not self.is_log_file(filepath):
            return
            
        self.check_file(filepath)
    
    def should_monitor_directory(self, dir_path):
        """Check if a directory should be monitored based on its path."""
        path_str = str(dir_path).lower()
        # Monitor directories that contain DDmisID workflow patterns
        indicators = [
            'control', 'target', 'kaon', 'pion', 'proton', 'electron', 'muon', 'ghost',
            'up', 'down', '2015', '2016', '2017', '2018', 'pideffx', 'workflow',
            'logs', 'engine', 'snakemake', '.snakemake',
            # Add particle transition patterns
            '_to_', '_like', 'proton_to_electron', 'electron_to_pion', 
            'kaon_to_', 'pion_to_', 'muon_to_', 'ghost_to_'
        ]
        return any(indicator in path_str for indicator in indicators)
    
    def add_directory_monitoring(self, dir_path):
        """Add monitoring for a new directory."""
        dir_str = str(dir_path)
        if dir_str not in self.monitored_dirs:
            self.monitored_dirs.add(dir_str)
            self.observer.schedule(self, dir_str, recursive=True)
            print(f"📂 Started monitoring new directory: {dir_path}")
    
    def is_log_file(self, filepath):
        """Check if a file is a log file we should monitor."""
        return (filepath.suffix in ['.log', '.txt'] or 
                'log' in filepath.name.lower() or
                filepath.name in ['pideffx.log', 'process_pideffx.log', 'ddmisid_log', 'snakemake.log'] or
                filepath.name.startswith('pideffx') or
                filepath.name.endswith('pideffx.log'))
    
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
                
                # Look for different types of authentication prompts
                self.check_for_auth_prompts(filepath, new_content)
                        
        except Exception:
            # Silently handle file access errors (file might be locked by Snakemake)
            pass
    
    def check_for_auth_prompts(self, filepath, text):
        """Check for various authentication patterns and display prompts."""
        
        # Check for OIDC device flow initiation
        if self.patterns['oidc_flow'].search(text) or self.patterns['token_required'].search(text):
            device_code = self.extract_device_code(text)
            auth_url = self.extract_auth_url(text)
            
            prompt_id = f"{filepath}_{device_code}_{auth_url}"
            if prompt_id not in self.shown_codes:
                self.shown_codes.add(prompt_id)
                self.display_oidc_prompt(filepath, device_code, auth_url, text)
        
        # Check for general SSO prompts
        elif self.patterns['sso'].search(text):
            device_code = self.extract_device_code(text)
            auth_url = self.extract_auth_url(text)
            
            prompt_id = f"{filepath}_{device_code}_{auth_url}"
            if prompt_id not in self.shown_codes and (device_code or auth_url):
                self.shown_codes.add(prompt_id)
                self.display_prompt(filepath, device_code, auth_url)
    
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
    
    def extract_auth_url(self, text):
        """Extract authentication URL from text."""
        match = self.patterns['auth_url'].search(text)
        return match.group(0) if match else None
    
    def display_oidc_prompt(self, filepath, device_code, auth_url, full_text):
        """Display OIDC-specific authentication prompt with enhanced information."""
        timestamp = time.strftime("%H:%M:%S")
        
        # Extract meaningful info from the path
        path_parts = filepath.parts
        context_info = self.extract_context_from_path(path_parts)
        
        print(f"\n{'='*80}")
        print(f"🔐 CERN OIDC AUTHENTICATION REQUIRED at {timestamp}")
        print(f"📄 Log File: {filepath.name}")
        print(f"📁 Location: {filepath.parent}")
        if context_info:
            print(f"🎯 DDmisID Context: {context_info}")
        print(f"{'='*80}")
        
        if device_code:
            print(f"🔑 Device Code: {device_code}")
        if auth_url:
            print(f"🔗 Authentication URL: {auth_url}")
        else:
            print(f"🔗 Default Auth URL: https://auth.cern.ch/auth/realms/cern/device")
        
        if device_code and not auth_url:
            print(f"🔗 Direct Link: https://auth.cern.ch/auth/realms/cern/device?user_code={device_code}")
            
        print(f"{'='*80}")
        print(f"📱 INSTRUCTIONS:")
        print(f"   1. Open the URL above in your browser")
        print(f"   2. Enter the device code if prompted")
        print(f"   3. Complete CERN SSO authentication")
        print(f"   4. Your DDmisID workflow will continue automatically")
        print(f"{'='*80}")
        print(f"⏳ Workflow paused - waiting for authentication...")
        print(f"📋 Process: DDmisID Snakemake workflow")
        print(f"{'='*80}\n")
        
        # Show relevant portions of the log for context
        lines = full_text.split('\n')
        auth_lines = [line for line in lines if any(pattern.search(line) for pattern in self.patterns.values())]
        if auth_lines:
            print("📝 Related log entries:")
            for line in auth_lines[-3:]:  # Show last 3 relevant lines
                print(f"   {line.strip()}")
            print()
    
    def display_prompt(self, filepath, device_code, auth_url):
        """Display general authentication prompt."""
        timestamp = time.strftime("%H:%M:%S")
        
        # Extract meaningful info from the path
        path_parts = filepath.parts
        context_info = self.extract_context_from_path(path_parts)
        
        print(f"\n{'='*80}")
        print(f"🔐 AUTHENTICATION REQUIRED at {timestamp}")
        print(f"📄 File: {filepath.name}")
        print(f"📁 Location: {filepath.parent}")
        if context_info:
            print(f"🎯 Context: {context_info}")
        print(f"{'='*80}")
        
        if auth_url:
            print(f"🔗 Go to: {auth_url}")
        else:
            print(f"🔗 Go to: https://auth.cern.ch/auth/realms/cern/device")
            
        if device_code:
            print(f"🔑 Enter code: {device_code}")
            print(f"🔗 Direct link: https://auth.cern.ch/auth/realms/cern/device?user_code={device_code}")
        
        print(f"{'='*80}")
        print(f"⏳ Process will continue after you authenticate in browser...")
        print(f"{'='*80}\n")
    
    def scan_for_existing_pideffx_logs(self, base_dirs):
        """Scan existing directories for pideffx.log files and start monitoring them."""
        pideffx_files_found = []
        
        for base_dir in base_dirs:
            if not base_dir.exists():
                continue
                
            # Look for pideffx.log files recursively
            pideffx_files = list(base_dir.rglob('pideffx.log')) + list(base_dir.rglob('*pideffx.log'))
            
            for pideffx_file in pideffx_files:
                pideffx_files_found.append(pideffx_file)
                # Initialize file position to current end (don't show historical content)
                self.file_positions[str(pideffx_file)] = pideffx_file.stat().st_size if pideffx_file.exists() else 0
                
                # Also monitor the parent directory if not already monitored
                parent_dir = pideffx_file.parent
                parent_str = str(parent_dir)
                if parent_str not in self.monitored_dirs:
                    self.monitored_dirs.add(parent_str)
                    self.observer.schedule(self, parent_str, recursive=False)
        
        return pideffx_files_found
    
    def extract_context_from_path(self, path_parts):
        """Extract meaningful context from file path for DDmisID workflow."""
        context = []
        
        # Look for year
        years = ['2015', '2016', '2017', '2018']
        year = next((part for part in path_parts if part in years), None)
        if year:
            context.append(f"Year {year}")
        
        # Look for magnet polarity
        polarities = ['up', 'down']
        polarity = next((part for part in path_parts if part in polarities), None)
        if polarity:
            context.append(f"Magnet {polarity}")
        
        # Look for region
        regions = ['control', 'target']
        region = next((part for part in path_parts if part in regions), None)
        if region:
            context.append(f"{region.title()} region")
        
        # Look for particle species (original particle)
        species = ['kaon', 'pion', 'proton', 'electron', 'muon', 'ghost']
        particle = next((part for part in path_parts if part in species), None)
        if particle:
            context.append(f"{particle.title()} species")
        
        # Look for particle transition patterns (e.g., proton_to_electron_like)
        transition_patterns = ['_to_', '_like']
        for part in path_parts:
            if any(pattern in part for pattern in transition_patterns):
                # Clean up the transition name for display
                transition = part.replace('_', ' ').replace(' like', '-like').title()
                context.append(f"PID: {transition}")
                break
        
        # Look for DDmisID workflow stages
        stages = ['pideffx', 'discretize', 'collect', 'engine']
        stage = next((part for part in path_parts if part in stages), None)
        if stage:
            context.append(f"{stage.title()} stage")
        
        return " | ".join(context)


def main():
    """Main monitoring function."""
    print("🔐 DDmisID Authentication Prompt Monitor v2.0")
    print("=" * 50)
    print("Enhanced monitoring for DDmisID Snakemake workflows")
    print("Monitors OIDC device flow, Kerberos, and general auth prompts")
    print("Run this in a separate terminal while your DDmisID workflow runs.")
    print("Press Ctrl+C to stop monitoring.\n")
    
    # Determine directories to monitor
    if len(sys.argv) > 1:
        monitor_dirs = [Path(sys.argv[1])]
    else:
        # Default directories for DDmisID - prioritize likely locations
        monitor_dirs = [
            Path("logs"),           # Main DDmisID logs
            Path("workflow"),       # Snakemake workflow logs
            Path(".snakemake"),     # Snakemake internal logs
            Path("scratch"),        # Temporary processing files
        ]
    
    # Check directories and provide user feedback
    print("🔍 Checking monitoring directories:")
    existing_dirs = []
    for d in monitor_dirs:
        if d.exists():
            print(f"   ✅ {d.absolute()} (exists)")
            existing_dirs.append(d)
        else:
            print(f"   📋 {d.absolute()} (will monitor when created)")
    
    # Set up monitoring with observer
    observer = Observer()
    event_handler = AuthPromptWatcher(observer)
    
    # Monitor existing directories
    if existing_dirs:
        for d in existing_dirs:
            observer.schedule(event_handler, str(d), recursive=True)
    
    # Always monitor current directory to catch new workflow directories
    observer.schedule(event_handler, ".", recursive=True)
    print(f"   📂 {Path('.').absolute()} (current directory - always monitored)")
    
    # Scan for existing pideffx.log files
    print("\n🔍 Scanning for existing pideffx.log files...")
    pideffx_files = event_handler.scan_for_existing_pideffx_logs(existing_dirs + [Path(".")])
    if pideffx_files:
        print(f"   📄 Found {len(pideffx_files)} existing pideffx.log files:")
        for pf in pideffx_files[:5]:  # Show first 5
            print(f"      - {pf}")
        if len(pideffx_files) > 5:
            print(f"      - ... and {len(pideffx_files) - 5} more")
    else:
        print("   📋 No existing pideffx.log files found (will monitor as they're created)")
    
    print()
    print("🎯 Monitoring patterns:")
    print("   - CERN OIDC device flow authentication")
    print("   - Kerberos authentication prompts") 
    print("   - logs/engine/ddmisid_log_*.log (engine logs)")
    print("   - logs/workflow/**/pideffx.log (PID efficiency extraction logs)")
    print("   - logs/workflow/**/process_pideffx.log (processed PID logs)")
    print("   - .snakemake/log/*.log (Snakemake internal logs)")
    print("   - Nested workflow directories (YEAR/POLARITY/REGION/SPECIES/*/pideffx.log)")
    print("   - Any .log or .txt files in workflow directories")
    print("   - Dynamically created subdirectories")
    print()
    
    observer.start()
    print("✅ Authentication monitor started!")
    print("   🔍 Watching for authentication prompts...")
    print("   📊 This will not interfere with your DDmisID workflow")
    print("   📂 New directories will be monitored automatically")
    print("   🔄 Enhanced OIDC and device flow detection")
    print()
    print("💡 TIP: Keep this terminal visible while running 'ddmisid-engine run'")
    print()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n⏹️  Stopping authentication monitor...")
        observer.stop()
    
    observer.join()
    print("✅ Authentication monitor stopped.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except ImportError as e:
        print(f"❌ Error: Missing dependency - {e}")
        print("📦 Install dependencies with:")
        print("   pip install watchdog")
        print("   or")
        print("   pip install -r requirements-auth-monitoring.txt")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)