# Authentication Prompt Display for DDmisID

## Overview

The DDmisID authentication prompt display system monitors log files in real-time and shows CERN OIDC authentication prompts in your main terminal, so you don't have to hunt through multiple log files to find them.

## Problem Statement

When running DDmisID workflows, subprocess tools like PIDCalib2 sometimes prompt for authentication. These prompts appear buried in log files, creating problems:

1. **Hidden prompts** - Authentication requests are buried in log files among thousands of lines
2. **Process waiting** - Your workflow hangs while waiting for authentication you can't see
3. **Manual searching** - You have to search through multiple log files to find the prompt
4. **Delayed response** - By the time you find the prompt, you've lost valuable processing time

## Solution: Real-time Prompt Display

The system monitors log files and displays authentication prompts prominently in your main terminal:

```
======================================================================
� AUTHENTICATION REQUIRED (from pidcalib_electron_job.log)
======================================================================
📱 Go to: https://auth.cern.ch/auth/realms/cern/device
🔑 Enter code: ZPXN-ZNKP
🔗 Or click: https://auth.cern.ch/auth/realms/cern/device?user_code=ZPXN-ZNKP
======================================================================
⏳ Waiting for authentication... (process will continue automatically)
======================================================================
```

## How It Works

### � **Real-time Log Monitoring**
- Watches log directories using file system events (no polling)
- Detects changes in `.log`, `.txt` files or files containing "log" in the name
- Only processes new content added since last check

### � **Pattern Recognition**
Detects these patterns in log files:
- `CERN SINGLE SIGN-ON`
- `device?user_code=XXXX-XXXX` (extracts the device code)
- Direct device codes like `ZPXN-ZNKP` on their own lines

### 🎯 **Smart Display**
- Shows prompts immediately in your main terminal
- Extracts device codes automatically
- Provides clickable URLs for easy authentication
- Avoids duplicate notifications for the same code

## Usage

### Automatic Integration (Default)

Simply run your DDmisID workflow as usual:

```bash
ddmisid-engine run -- --cores 4
```

The system automatically:
- Monitors `logs/`, `workflow/logs/`, and `.snakemake/log/` directories
- Displays authentication prompts in your terminal
- Keeps running while you authenticate in your browser

### Test the System

```bash
# Test the monitoring system
ddmisid-engine test-auth-monitor

# Run a simple demo
python demo_simple_auth_monitor.py
```

### Manual Integration

For custom workflows:

```python
from ddmisid.auth_monitor import create_auth_monitor
from pathlib import Path

# Monitor specific directories
with create_auth_monitor() as monitor:
    monitor.start_monitoring([Path("logs"), Path("custom_logs")])
    
    # Your workflow code here
    # Authentication prompts will be displayed automatically
    run_your_pidcalib_jobs()
```

## Typical Workflow

1. **Start your workflow**: `ddmisid-engine run -- --cores 4`
2. **System starts monitoring**: Log files are watched automatically
3. **PIDCalib2 jobs run**: Multiple processes create log files
4. **Authentication needed**: One process needs OIDC authentication
5. **Prompt displayed**: You see the prompt immediately in your terminal:
   ```
   🔐 AUTHENTICATION REQUIRED (from pidcalib_kaon_job.log)
   📱 Go to: https://auth.cern.ch/auth/realms/cern/device
   🔑 Enter code: ZPXN-ZNKP
   ```
6. **You authenticate**: Open browser, enter code
7. **Process continues**: PIDCalib2 job resumes automatically
8. **Workflow completes**: All jobs finish successfully

## Configuration

### Default Monitoring Locations
- `logs/` - Standard DDmisID log directory
- `workflow/logs/` - Snakemake workflow logs  
- `.snakemake/log/` - Snakemake internal logs

### Monitored File Types
- Files ending in `.log`
- Files ending in `.txt`
- Files with "log" in the filename

### Custom Monitoring

```python
from ddmisid.auth_monitor import AuthPromptMonitor

# Create custom monitor
monitor = AuthPromptMonitor()

# Add custom directories
custom_dirs = [Path("my_logs"), Path("pidcalib_outputs")]
monitor.start_monitoring(custom_dirs)

try:
    # Your workflow
    run_custom_jobs()
finally:
    monitor.stop_monitoring()
```

## Error Handling

### Missing Dependencies
If `watchdog` is not installed, DDmisID falls back to standard execution without monitoring:
```bash
pip install watchdog
```

### File Access Issues
- Missing log directories are silently skipped
- File permission errors don't stop monitoring
- Locked files during writing are handled gracefully

### No False Positives
- Only displays prompts with valid device codes
- Avoids duplicate notifications
- Ignores old log content when starting

## Performance

### Efficiency
- Uses file system events (no polling)
- Minimal CPU and memory usage
- Only processes new log content
- Regex patterns compiled once at startup

### Scalability  
- Can monitor hundreds of log files simultaneously
- No impact on main workflow performance
- Automatic cleanup when monitoring stops

## Troubleshooting

### Q: Authentication prompts not showing
**Solutions:**
- Check that log files have `.log`, `.txt` extensions or contain "log"
- Verify the log directories exist and are writable
- Ensure `watchdog` is installed: `pip install watchdog`

### Q: System shows old prompts
**Solutions:**
- The system only shows new prompts that appear after monitoring starts
- If you see old prompts, they're likely from a new process writing to the same log file

### Q: Multiple prompts for same code
**Solutions:**
- The system automatically deduplicates based on device codes
- If you see duplicates, they likely have different codes

## Integration with Existing Tools

### Snakemake Integration
Automatically integrated - no changes needed to your Snakemake workflows.

### PIDCalib2 Compatibility
Works with any version of PIDCalib2 that outputs standard OIDC prompts.

### CERN Infrastructure
- Uses standard CERN OIDC device flow
- No custom authentication methods
- Compatible with existing token management

## Example Output

When running your DDmisID workflow, instead of authentication prompts being buried in log files like this:

```
# Hidden in logs/pidcalib/electron/job_2024_up.log (line 1,247 of 2,500)
Processing calibration file 15 of 200...
CERN SINGLE SIGN-ON
On your tablet, phone or computer, go to:
https://auth.cern.ch/auth/realms/cern/device  
and enter the following code:
ZPXN-ZNKP
Waiting for authentication...
```

You'll see this prominently in your main terminal:

```
======================================================================
🔐 AUTHENTICATION REQUIRED (from job_2024_up.log)
======================================================================
📱 Go to: https://auth.cern.ch/auth/realms/cern/device
🔑 Enter code: ZPXN-ZNKP
🔗 Or click: https://auth.cern.ch/auth/realms/cern/device?user_code=ZPXN-ZNKP
======================================================================
⏳ Waiting for authentication... (process will continue automatically)
======================================================================
```

## Security

- **No token handling** - System only displays prompts, doesn't manage tokens
- **Read-only monitoring** - Only reads log files, never modifies them
- **Standard CERN auth** - Uses official CERN OIDC device flow
- **No network access** - Monitoring happens locally on your filesystem