#!/usr/bin/env python3
"""
Quick test script for the DDmisID authentication monitoring system.
Run this to verify the monitoring system is working correctly.
"""

import sys
import tempfile
import time
from pathlib import Path
import typing_extensions
def test_pattern_detection():
    """Test that regex patterns correctly detect authentication prompts."""
    print("🔍 Testing pattern detection...")
    
    try:
        from ddmisid.auth_monitor import AuthPatternDetector
        
        detector = AuthPatternDetector()
        
        # Test OIDC pattern
        oidc_text = """
        CERN SINGLE SIGN-ON
        On your tablet, phone or computer, go to:
        https://auth.cern.ch/auth/realms/cern/device
        and enter the following code:
        TEST-1234
        You may also open the following link directly:
        https://auth.cern.ch/auth/realms/cern/device?user_code=TEST-1234
        """
        
        oidc_result = detector.detect_oidc_prompt(oidc_text)
        if oidc_result and 'extracted_code' in oidc_result:
            print(f"✅ OIDC detection working - extracted code: {oidc_result['extracted_code']}")
        else:
            print("❌ OIDC detection failed")
            return False
        
        # Test Kerberos pattern  
        kerberos_text = "Password for user@CERN.CH:"
        kerberos_result = detector.detect_kerberos_prompt(kerberos_text)
        if kerberos_result:
            print("✅ Kerberos detection working")
        else:
            print("❌ Kerberos detection failed")
            return False
            
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False


def test_file_monitoring():
    """Test that file monitoring detects changes in log files."""
    print("📁 Testing file monitoring...")
    
    try:
        from ddmisid.auth_monitor import create_monitoring_context
        
        # Create temporary log file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
            log_path = Path(f.name)
            f.write("Initial log content\n")
        
        detected_auth = False
        
        def auth_callback(filepath, detection):
            nonlocal detected_auth
            detected_auth = True
            print(f"✅ Authentication prompt detected in {Path(filepath).name}")
        
        # Start monitoring
        with create_monitoring_context() as monitor:
            # Override the callback for testing
            monitor._handle_auth_prompt = auth_callback
            monitor.start_monitoring([], [log_path])
            
            # Add authentication prompt to file
            with open(log_path, 'a') as f:
                f.write("CERN SINGLE SIGN-ON\n")
                f.write("device?user_code=TEST-CODE\n")
            
            # Wait for detection
            time.sleep(2)
        
        # Cleanup
        log_path.unlink()
        
        if detected_auth:
            print("✅ File monitoring working")
            return True
        else:
            print("❌ File monitoring failed to detect changes")
            return False
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Monitoring test failed: {e}")
        return False


def test_cli_integration():
    """Test that CLI integration is working."""
    print("🖥️  Testing CLI integration...")
    
    try:
        from ddmisid.cli import cli
        from click.testing import CliRunner
        
        runner = CliRunner()
        result = runner.invoke(cli, ['test-auth-monitor'])
        
        if result.exit_code == 0:
            print("✅ CLI integration working")
            return True
        else:
            print(f"❌ CLI test failed with exit code {result.exit_code}")
            print(f"Output: {result.output}")
            return False
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ CLI test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("🔐 DDmisID Authentication Monitoring System Test")
    print("="*55)
    
    tests = [
        test_pattern_detection,
        test_file_monitoring,
        test_cli_integration,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
            print()  # Add spacing between tests
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
            print()
    
    print("="*55)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Authentication monitoring is ready to use.")
        print("\nNext steps:")
        print("1. Install dependencies: pip install -e .")
        print("2. Run DDmisID workflows: ddmisid-engine run -- --cores 4")
        print("3. Authentication prompts will be handled automatically!")
        return 0
    else:
        print("⚠️  Some tests failed. Check the error messages above.")
        print("\nTroubleshooting:")
        print("- Ensure all dependencies are installed: pip install watchdog")
        print("- Check that you're in the DDmisID directory")
        print("- Verify Python version >= 3.8")
        return 1


if __name__ == "__main__":
    sys.exit(main())