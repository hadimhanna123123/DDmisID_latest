#!/usr/bin/env python3
"""
Simple demonstration of authentication prompt monitoring.
This shows how authentication prompts from PIDCalib2 log files will be displayed in your terminal.
"""

import time
import tempfile
from pathlib import Path

def demo_auth_monitoring():
    """Show how authentication prompts will appear in your terminal."""
    
    print("🔐 DDmisID Authentication Prompt Display Demo")
    print("=" * 50)
    print("This demonstrates how authentication prompts buried in log files")
    print("will be displayed prominently in your main terminal.\n")
    
    # Import the monitoring system
    try:
        from ddmisid.auth_monitor import create_auth_monitor
    except ImportError:
        print("❌ Error: Install dependencies first with: pip install watchdog")
        return
    
    # Create a temporary log directory (simulating your workflow logs)
    temp_dir = Path(tempfile.mkdtemp(suffix="_demo_logs"))
    pidcalib_log = temp_dir / "pidcalib_electron_job.log"
    
    print(f"📁 Simulating log files in: {temp_dir}")
    print("🚀 Starting monitoring...")
    
    # Start monitoring
    with create_auth_monitor() as monitor:
        monitor.start_monitoring([temp_dir])
        
        print("✅ Monitoring started - watching for authentication prompts\n")
        
        # Simulate a PIDCalib2 job starting
        print("📝 Simulating PIDCalib2 job writing to log file...")
        with open(pidcalib_log, 'w') as f:
            f.write("Starting PIDCalib2 job for electron calibration...\n")
            f.write("Loading calibration samples...\n")
            f.write("Connecting to storage system...\n")
        
        time.sleep(1)
        
        # Simulate the authentication prompt appearing in the log
        print("💥 Simulating authentication prompt appearing in log file...")
        print("   (This is what would normally be buried in the log file)\n")
        
        with open(pidcalib_log, 'a') as f:
            f.write("Processing calibration data...\n")
            f.write("CERN SINGLE SIGN-ON\n")
            f.write("\n")
            f.write("On your tablet, phone or computer, go to:\n")
            f.write("https://auth.cern.ch/auth/realms/cern/device\n")
            f.write("and enter the following code:\n")
            f.write("DEMO-CODE\n")
            f.write("\n")
            f.write("You may also open the following link directly:\n")
            f.write("https://auth.cern.ch/auth/realms/cern/device?user_code=DEMO-CODE\n")
        
        # Give the monitor time to detect and display the prompt
        print("⏳ Waiting for prompt detection...")
        time.sleep(2)
        
        print("\n📋 The above is what you'll see when authentication is needed!")
        print("   No need to hunt through log files anymore.\n")
        
        # Simulate continuing after authentication
        with open(pidcalib_log, 'a') as f:
            f.write("Authentication completed - continuing processing...\n")
            f.write("Generating efficiency histograms...\n")
            f.write("Job completed successfully.\n")
        
        print("✅ In your real workflow, after you authenticate in the browser,")
        print("   the PIDCalib2 processes will continue automatically.")
    
    # Cleanup
    for file in temp_dir.glob("*"):
        file.unlink()
    temp_dir.rmdir()
    
    print(f"\n🎉 Demo completed!")
    print("💡 When you run 'ddmisid-engine run', authentication prompts")
    print("   from ANY log file will be displayed in your terminal like this.")


if __name__ == "__main__":
    demo_auth_monitoring()