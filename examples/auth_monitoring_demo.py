#!/usr/bin/env python3
"""
Example script demonstrating the DDmisID authentication monitoring system.

This script simulates a workflow that generates authentication prompts in log files,
showing how the monitoring system detects and handles them in real-time.
"""

import time
import tempfile
from pathlib import Path
from ddmisid.auth_monitor import create_monitoring_context
import logging

# Setup logging to see the monitoring in action
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def simulate_pidcalib_workflow():
    """Simulate a PIDCalib2 workflow that generates authentication prompts."""
    
    # Create temporary log files
    temp_dir = Path(tempfile.mkdtemp(suffix="_ddmisid_logs"))
    log_file = temp_dir / "pidcalib_job.log"
    
    print(f"📁 Created temporary log directory: {temp_dir}")
    print(f"📄 Log file: {log_file}")
    
    # Initial log content
    with open(log_file, 'w') as f:
        f.write("Starting PIDCalib2 job...\n")
        f.write("Loading calibration data...\n")
        f.write("Connecting to storage system...\n")
    
    print("\n🚀 Starting workflow simulation with authentication monitoring...")
    
    # Start monitoring
    with create_monitoring_context("ddmisid") as monitor:
        monitor.start_monitoring([temp_dir])
        
        print("✅ Authentication monitoring started")
        print("🔍 Watching for authentication prompts in log files...")
        
        # Simulate workflow progress
        time.sleep(2)
        
        # Simulate first authentication prompt (this would normally come from PIDCalib2)
        print("\n💥 Simulating OIDC authentication prompt from PIDCalib2...")
        with open(log_file, 'a') as f:
            f.write("\nProcessing calibration files...\n")
            f.write("CERN SINGLE SIGN-ON\n")
            f.write("\n")
            f.write("On your tablet, phone or computer, go to:\n")
            f.write("https://auth.cern.ch/auth/realms/cern/device\n")
            f.write("and enter the following code:\n")
            f.write("DEMO-CODE\n")
            f.write("\n")
            f.write("You may also open the following link directly and follow the instructions:\n")
            f.write("https://auth.cern.ch/auth/realms/cern/device?user_code=DEMO-CODE\n")
            f.write("\n")
        
        # Give the monitor time to detect and handle the prompt
        print("⏱️  Waiting for authentication monitoring to detect the prompt...")
        time.sleep(3)
        
        # Continue with workflow
        with open(log_file, 'a') as f:
            f.write("Continuing with calibration processing...\n")
            f.write("Processing momentum bins...\n")
            f.write("Processing eta bins...\n")
        
        time.sleep(2)
        
        # Simulate another type of authentication issue
        print("\n💥 Simulating Kerberos authentication prompt...")
        kerberos_log = temp_dir / "kerberos_job.log"
        with open(kerberos_log, 'w') as f:
            f.write("Starting secondary process...\n")
            f.write("Password for user@CERN.CH:\n")
            f.write("kinit authentication expired\n")
        
        time.sleep(2)
        
        # Final workflow steps
        with open(log_file, 'a') as f:
            f.write("Finalizing efficiency histograms...\n")
            f.write("PIDCalib2 job completed successfully.\n")
        
        print("\n✅ Workflow simulation completed")
        print("🔍 Monitoring will stop when exiting context...")
    
    print(f"\n🧹 Cleaning up temporary files at {temp_dir}")
    # Cleanup
    for file in temp_dir.glob("*"):
        file.unlink()
    temp_dir.rmdir()
    
    print("✅ Example completed successfully!")


def demonstrate_manual_detection():
    """Demonstrate manual pattern detection without file monitoring."""
    from ddmisid.auth_monitor import AuthPatternDetector
    
    print("\n" + "="*60)
    print("🔍 MANUAL PATTERN DETECTION DEMO")
    print("="*60)
    
    detector = AuthPatternDetector()
    
    # Test OIDC detection
    oidc_sample = """
    Processing data files...
    CERN SINGLE SIGN-ON
    
    On your tablet, phone or computer, go to:
    https://auth.cern.ch/auth/realms/cern/device
    and enter the following code:
    ABCD-1234
    
    You may also open the following link directly and follow the instructions:
    https://auth.cern.ch/auth/realms/cern/device?user_code=ABCD-1234
    
    Waiting for authentication...
    """
    
    print("\n📝 Sample log content:")
    print(oidc_sample)
    
    detection = detector.detect_oidc_prompt(oidc_sample)
    if detection:
        print("\n✅ OIDC authentication prompt detected!")
        print(f"📋 Detected patterns: {list(detection.keys())}")
        if 'extracted_code' in detection:
            print(f"🔑 Device code: {detection['extracted_code']}")
    else:
        print("\n❌ No OIDC prompt detected")
    
    # Test Kerberos detection
    kerberos_sample = """
    Initializing connection...
    Password for hmhanna@CERN.CH:
    kinit: Password for hmhanna@CERN.CH expired
    """
    
    print(f"\n📝 Kerberos sample:")
    print(kerberos_sample)
    
    kerberos_detection = detector.detect_kerberos_prompt(kerberos_sample)
    if kerberos_detection:
        print("\n✅ Kerberos authentication prompt detected!")
        print(f"📋 Detected patterns: {list(kerberos_detection.keys())}")
    else:
        print("\n❌ No Kerberos prompt detected")


if __name__ == "__main__":
    print("🔐 DDmisID Authentication Monitoring System Demo")
    print("="*60)
    
    try:
        # First demonstrate manual pattern detection
        demonstrate_manual_detection()
        
        # Then demonstrate real-time monitoring
        print("\n" + "="*60)
        print("📡 REAL-TIME MONITORING DEMO")
        print("="*60)
        simulate_pidcalib_workflow()
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted by user")
    except ImportError as e:
        print(f"\n❌ Missing dependencies: {e}")
        print("💡 Install with: pip install watchdog")
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()