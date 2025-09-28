# Authentication Monitoring System for DDmisID

## Overview

The DDmisID authentication monitoring system provides real-time detection and handling of CERN OIDC and Kerberos authentication prompts that appear in subprocess log files during workflow execution.

## Problem Statement

When running DDmisID workflows, subprocess tools like PIDCalib2 may prompt for authentication even when the main process has already authenticated. This creates several issues:

1. **Authentication prompts buried in log files** - Users don't see them immediately
2. **Workflow interruption** - Processes hang waiting for authentication
3. **Manual intervention required** - Users must manually authenticate and restart workflows
4. **Token expiration during long runs** - Multi-hour workflows may exceed token lifetimes

## Solution: Real-time Log Monitoring

The authentication monitoring system continuously watches log files and directories for authentication prompts using regex pattern matching, then automatically handles re-authentication while keeping the main processes running.

## Key Features

### 🔍 **Real-time Pattern Detection**
Monitors log files for specific authentication patterns:

**OIDC Patterns:**
- `CERN SINGLE SIGN-ON`
- `On your tablet, phone or computer, go to:`
- `https://auth.cern.ch/auth/realms/cern/device`
- `and enter the following code:`
- `device?user_code=XXXX-XXXX` (extracts the device code)

**Kerberos Patterns:**
- `Password for user@CERN.CH:`
- `kinit.*expired`
- `kinit.*failed`

### 🔄 **Automatic Re-authentication**
When OIDC prompts are detected:
1. Extracts the device code from log files
2. Displays user-friendly authentication instructions
3. Automatically runs `auth-get-user-token` to refresh tokens
4. Updates environment variables for subprocesses

### 📁 **Flexible Monitoring**
- **Directory monitoring**: Watches entire log directories recursively
- **Specific file monitoring**: Monitors individual log files
- **Pattern-based detection**: Only monitors files with `.log`, `.txt` extensions or "log" in filename

### 🛡️ **Thread-safe Operation**
- Uses file system event handlers for efficient monitoring
- Thread-safe authentication handling prevents race conditions
- Maintains file read positions to avoid re-processing old log content

## Usage

### Automatic Integration (Recommended)

The monitoring system is automatically integrated into the DDmisID engine. Simply run:

```bash
ddmisid-engine run -- --cores 4
```

The system will automatically:
- Start monitoring `logs/`, `workflow/logs/`, and `.snakemake/log/` directories
- Detect authentication prompts in real-time
- Handle re-authentication automatically
- Display user-friendly messages when manual intervention is needed

### Manual Integration

For custom workflows, you can use the monitoring system directly:

```python
from ddmisid.auth_monitor import create_monitoring_context
from pathlib import Path

# Monitor specific directories and files
log_dirs = [Path("logs"), Path("custom_logs")]
specific_files = [Path("important.log")]

with create_monitoring_context("ddmisid") as monitor:
    monitor.start_monitoring(log_dirs, specific_files)
    
    # Your workflow code here
    # The monitor runs in the background
    run_your_workflow()
```

### Advanced Usage

For fine-grained control:

```python
from ddmisid.auth_monitor import AuthMonitorManager
from pathlib import Path

# Create and configure the monitor
monitor = AuthMonitorManager(client_id="ddmisid")

# Start monitoring
monitor.start_monitoring(
    log_directories=[Path("logs")],
    specific_files=[Path("critical.log")]
)

try:
    # Your long-running workflow
    run_pidcalib_jobs()
finally:
    monitor.stop_monitoring()
```

## Authentication Flow

### OIDC Authentication Detection

When the system detects an OIDC prompt:

```
🔐 OIDC authentication required (detected in pidcalib_job.log)
📱 Device code detected: TLIF-MMHA

============================================================
🔐 AUTHENTICATION REQUIRED
📱 Go to: https://auth.cern.ch/auth/realms/cern/device
🔑 Enter code: TLIF-MMHA
============================================================

🔄 Attempting automatic OIDC re-authentication...
✅ OIDC re-authentication successful
```

### Kerberos Authentication Detection

When Kerberos authentication is needed:

```
🎫 Kerberos authentication required (detected in job.log)

============================================================
🎫 KERBEROS AUTHENTICATION REQUIRED
Please run: kinit <username>@CERN.CH
============================================================
```

## Configuration

The monitoring system uses these default paths:
- **Token storage**: `~/.cache/cern-oidc/`
- **Log directories**: `logs/`, `workflow/logs/`, `.snakemake/log/`
- **Client ID**: `ddmisid`

You can customize these by:

```python
from ddmisid.auth_monitor import AuthMonitorManager

# Custom client ID
monitor = AuthMonitorManager(client_id="custom-client")

# Custom log directories
custom_dirs = [Path("custom/logs"), Path("another/logdir")]
monitor.start_monitoring(custom_dirs)
```

## Error Handling

The system gracefully handles various error conditions:

### Missing Dependencies
If the `watchdog` library is not available, DDmisID falls back to standard execution without monitoring.

### File System Errors
- Missing log directories are skipped with warnings
- File permission errors are logged but don't stop monitoring
- Corrupted log files are handled with encoding fallbacks

### Authentication Failures
- Failed automatic re-authentication triggers manual intervention messages
- Multiple authentication attempts are prevented with thread locks
- Clear error messages guide users through manual authentication

## Integration with Snakemake

The monitoring system integrates seamlessly with Snakemake workflows:

```python
from ddmisid.auth_monitor import monitor_snakemake_logs

# Run Snakemake with authentication monitoring
monitor_snakemake_logs(["--cores", "4", "--verbose"], client_id="ddmisid")
```

This automatically:
- Starts monitoring before Snakemake execution
- Handles authentication prompts during the workflow
- Stops monitoring when Snakemake completes
- Preserves all Snakemake functionality and error handling

## Testing

Test the monitoring system:

```bash
cd /path/to/ddmisid
python -m ddmisid.auth_monitor test
```

This creates a test log file with authentication prompts and verifies the detection system works correctly.

## Performance Considerations

### Efficiency
- Uses file system events instead of polling for minimal CPU usage
- Only processes new log content since last read
- Regex compilation is done once at startup

### Memory Usage
- Maintains minimal state (file positions and handles)
- Automatic cleanup when monitoring stops
- No log content is stored in memory

### Scalability
- Can monitor hundreds of log files simultaneously
- Thread-safe design allows concurrent authentication handling
- Minimal impact on main workflow performance

## Troubleshooting

### Common Issues

**Q: Authentication prompts are not detected**
- Check that log files have `.log`, `.txt` extensions or contain "log" in filename
- Verify the log directory is being monitored
- Check file permissions allow reading

**Q: Automatic re-authentication fails**
- Ensure `auth-get-user-token` is available in PATH
- Check CERN network connectivity
- Verify client ID is registered with CERN OIDC

**Q: Monitoring stops unexpectedly**
- Check system logs for file system errors
- Ensure log directories weren't deleted during workflow
- Verify sufficient disk space for log files

### Debug Mode

Enable detailed logging:

```python
import logging
logging.getLogger("ddmisid.auth_monitor").setLevel(logging.DEBUG)
```

### Manual Fallback

If monitoring fails, you can always authenticate manually:

```bash
# OIDC authentication
auth-get-user-token -c ddmisid -v

# Kerberos authentication
kinit <username>@CERN.CH

# Export tokens for subprocesses
export CERN_OIDC_TOKEN=$(cat ~/.cache/cern-oidc/access.token)
```

## Security Considerations

### Token Security
- Token files are created with restricted permissions (600)
- Token directory has secure permissions (700)
- Tokens are never logged or displayed in plaintext

### Process Security
- Monitoring runs with same privileges as main process
- No elevation of privileges required
- Authentication uses official CERN tools

### Network Security
- All authentication uses HTTPS
- Standard CERN OIDC security protocols
- No custom authentication implementations