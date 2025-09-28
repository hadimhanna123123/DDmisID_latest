#!/usr/bin/env python3
"""
Test script for the DDmisID authentication monitoring system.
Creates fake log entries to verify the monitoring script detects them correctly.
"""

import time
import os
from pathlib import Path

def create_test_log_with_auth_prompt():
    """Create a test log file with authentication prompts to verify monitoring."""
    
    # Create test log directory
    test_log_dir = Path("logs/engine")
    test_log_dir.mkdir(parents=True, exist_ok=True)
    
    # Create test log file
    test_log_file = test_log_dir / f"ddmisid_log_test_{int(time.time())}.log"
    
    print(f"🧪 Creating test log file: {test_log_file}")
    print("📝 This will simulate authentication prompts for testing")
    print("🔍 Make sure your watch_auth_prompts.py is running in another terminal")
    print()
    
    # Write initial log content
    with open(test_log_file, "w") as f:
        f.write("2025-09-28 15:30:00 | INFO | DDmisID engine starting\n")
        f.write("2025-09-28 15:30:01 | INFO | Loading configuration\n")
        f.write("2025-09-28 15:30:02 | INFO | Starting Snakemake workflow\n")
    
    print("✅ Initial log content written")
    time.sleep(2)
    
    # Add OIDC authentication prompt
    print("🔐 Adding OIDC authentication prompt...")
    with open(test_log_file, "a") as f:
        f.write("2025-09-28 15:30:05 | INFO | OIDC authentication required - starting device flow\n")
        f.write("2025-09-28 15:30:06 | INFO | Starting CERN OIDC device login (watch this terminal for the device code)...\n")
        f.write("2025-09-28 15:30:07 | INFO | Please go to https://auth.cern.ch/auth/realms/cern/device?user_code=ABCD-1234\n")
        f.write("2025-09-28 15:30:08 | INFO | Device code: ABCD-1234\n")
    
    time.sleep(3)
    
    # Add completion message
    print("✅ Adding authentication completion...")
    with open(test_log_file, "a") as f:
        f.write("2025-09-28 15:30:15 | INFO | OIDC authentication completed successfully\n")
        f.write("2025-09-28 15:30:16 | INFO | Exported OIDC access token to environment variables\n")
        f.write("2025-09-28 15:30:17 | INFO | Continuing DDmisID workflow\n")
    
    time.sleep(2)
    
    # Test with different authentication patterns
    print("🔐 Adding additional auth patterns for testing...")
    with open(test_log_file, "a") as f:
        f.write("2025-09-28 15:30:20 | INFO | CERN SINGLE SIGN-ON required\n")
        f.write("2025-09-28 15:30:21 | INFO | Go to: https://auth.cern.ch/auth/realms/cern/device\n")
        f.write("2025-09-28 15:30:22 | INFO | Enter code: EFGH-5678\n")
    
    print("🧪 Test completed!")
    print(f"📄 Test log file created at: {test_log_file}")
    print("🔍 Check if your monitoring script detected the authentication prompts")
    print()
    print("🗑️  Clean up: Delete the test log file when done testing")
    
    return test_log_file


def test_workflow_directory_monitoring():
    """Test monitoring of workflow-specific directories."""
    
    print("🧪 Testing workflow directory monitoring...")
    
    # Create workflow-like directory structure matching your examples
    test_dirs = [
        "logs/workflow/2018/up/control/proton/proton_to_electron_like",
        "logs/workflow/2018/up/control/electron/electron_to_pion_like",
        "logs/workflow/2018/down/target/kaon/kaon_to_muon_like",
    ]
    
    created_files = []
    
    for test_dir in test_dirs:
        dir_path = Path(test_dir)
        dir_path.mkdir(parents=True, exist_ok=True)
        
        # Create both pideffx.log and process_pideffx.log files
        for log_name in ["pideffx.log", "process_pideffx.log"]:
            log_file = dir_path / log_name
            print(f"📁 Creating test workflow log: {log_file}")
            created_files.append(log_file)
            
            with open(log_file, "w") as f:
                f.write(f"2025-09-28 15:35:00 | INFO | Starting {log_name.replace('.log', '')}\n")
                f.write(f"2025-09-28 15:35:01 | INFO | Processing {test_dir.split('/')[-1]} efficiency\n")
                f.write("2025-09-28 15:35:02 | INFO | Connecting to CERN services\n")
            
            time.sleep(1)
            
            # Add auth prompt
            with open(log_file, "a") as f:
                f.write("2025-09-28 15:35:05 | WARNING | CERN_OIDC_TOKEN not found in environment\n") 
                f.write("2025-09-28 15:35:06 | INFO | Starting CERN OIDC device login (watch this terminal for the device code)...\n")
                f.write(f"2025-09-28 15:35:07 | INFO | Please go to https://auth.cern.ch/auth/realms/cern/device?user_code=TEST-{hash(test_dir + log_name) % 10000:04d}\n")
    
    print("✅ Workflow directory test completed!")
    return created_files


if __name__ == "__main__":
    print("🧪 DDmisID Authentication Monitoring Test")
    print("=" * 50)
    print()
    
    # Check if monitoring script exists
    monitor_script = Path("watch_auth_prompts.py")
    if not monitor_script.exists():
        print("❌ Error: watch_auth_prompts.py not found!")
        print("   Make sure you're in the DDmisID project directory")
        exit(1)
    
    print("📋 INSTRUCTIONS:")
    print("1. Open another terminal in this directory")
    print("2. Run: python watch_auth_prompts.py")
    print("3. Come back to this terminal and press Enter to start tests")
    print()
    
    input("Press Enter when monitoring script is running...")
    
    # Run tests
    test_log = create_test_log_with_auth_prompt()
    
    print("\n" + "="*50)
    test_files = test_workflow_directory_monitoring()
    
    print("\n" + "="*50)
    print("🧪 All tests completed!")
    print()
    print("🧹 Cleanup (optional):")
    print(f"   rm {test_log}")
    for test_file in test_files[:3]:  # Show first few files
        print(f"   rm {test_file}")
    if len(test_files) > 3:
        print(f"   # ... and {len(test_files) - 3} more files")
    print("   rm -rf logs/workflow/2018  # Remove entire test workflow structure")