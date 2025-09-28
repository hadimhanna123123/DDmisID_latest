# DDmisID Authentication Monitoring

## Overview

The DDmisID library includes an authentication monitoring system that watches for CERN authentication prompts during Snakemake workflow execution. This allows you to see authentication requests in a separate terminal without interrupting your main workflow.

## The Problem

When running DDmisID workflows, the system may need to authenticate with CERN services (both Kerberos and OIDC) during execution. These authentication prompts can appear buried in log files or in the middle of complex Snakemake output, making them easy to miss.

## The Solution

The `watch_auth_prompts.py` script provides a standalone monitor that:

- Watches log files in real-time
- Detects various authentication patterns
- Displays clear, formatted authentication prompts
- Provides direct links and codes for easy authentication
- Runs independently without interfering with your workflow

## Usage

### Basic Usage

1. **Start the monitoring script** in a separate terminal:
   ```bash
   python watch_auth_prompts.py
   ```

2. **Run your DDmisID workflow** in your main terminal:
   ```bash
   ddmisid-engine run -- --cores 4
   ```

3. **Watch for authentication prompts** in the monitoring terminal. When authentication is needed, you'll see clear instructions like:

   ```
   ================================================================================
   🔐 CERN OIDC AUTHENTICATION REQUIRED at 15:30:07
   📄 Log File: pideffx.log
   📁 Location: logs/workflow/2018/up/control/proton/proton_to_electron_like
   🎯 DDmisID Context: Year 2018 | Magnet up | Control region | Proton species | PID: Proton To Electron-like
   ================================================================================
   🔑 Device Code: ABCD-1234
   🔗 Authentication URL: https://auth.cern.ch/auth/realms/cern/device?user_code=ABCD-1234
   ================================================================================
   📱 INSTRUCTIONS:
      1. Open the URL above in your browser
      2. Enter the device code if prompted
      3. Complete CERN SSO authentication
      4. Your DDmisID workflow will continue automatically
   ================================================================================
   ```

### Advanced Usage

Monitor a specific directory:
```bash
python watch_auth_prompts.py /path/to/custom/logs
```

### Installation

Install required dependencies:
```bash
pip install -r requirements-auth-monitoring.txt
```

Or manually:
```bash
pip install watchdog
```

## Monitored Locations

The script automatically monitors:

- `logs/engine/` - DDmisID engine logs
- `logs/workflow/` - Snakemake workflow stage logs including:
  - `logs/workflow/YEAR/POLARITY/REGION/SPECIES/*/pideffx.log` - PID efficiency extraction logs
  - `logs/workflow/YEAR/POLARITY/REGION/SPECIES/*/process_pideffx.log` - Processed PID logs  
- `.snakemake/log/` - Snakemake internal logs
- `workflow/` - Workflow directory
- `scratch/` - Temporary processing files
- Any dynamically created subdirectories during workflow execution

### Deep Nested Monitoring

The monitor specifically handles DDmisID's deep directory structure:
```
logs/workflow/2018/up/control/proton/proton_to_electron_like/pideffx.log
logs/workflow/2018/up/control/electron/electron_to_pion_like/process_pideffx.log
logs/workflow/2018/down/target/kaon/kaon_to_muon_like/pideffx.log
```

It automatically scans for existing `pideffx.log` files and monitors new ones as they're created.

## Detected Authentication Patterns

The monitor detects:

1. **OIDC Device Flow**
   - "Starting CERN OIDC device login"
   - "watch this terminal for the device code" 
   - Device codes in format `ABCD-1234`
   - URLs containing `auth.cern.ch`

2. **General Authentication**
   - "CERN SINGLE SIGN-ON"
   - "OIDC authentication required"
   - "CERN_OIDC_TOKEN not found"

3. **URLs and Codes**
   - Automatically extracts device codes
   - Parses authentication URLs
   - Creates direct authentication links

## Context Extraction

The monitor provides context about what part of the DDmisID workflow needs authentication:

- **Year**: 2015, 2016, 2017, 2018
- **Magnet Polarity**: up, down  
- **Region**: control, target
- **Particle Species**: kaon, pion, proton, electron, muon, ghost
- **Workflow Stage**: pideffx, discretize, collect, engine

## Testing

Test the monitoring system:

```bash
python test_auth_monitoring.py
```

This creates fake authentication prompts to verify the monitor works correctly.

## Integration with DDmisID

The monitoring script is designed to work seamlessly with the DDmisID authentication system:

### DDmisID Authentication Flow
1. **Engine Start**: `ddmisid-engine run` starts
2. **OIDC Check**: System checks for existing OIDC tokens
3. **Device Flow**: If no token, starts CERN OIDC device flow
4. **Monitor Detection**: The monitoring script detects the authentication prompt
5. **User Action**: User follows the displayed instructions to authenticate
6. **Workflow Continues**: DDmisID automatically continues once authenticated

### Multiple Authentication Points
DDmisID may require authentication at multiple points:
- Initial engine startup (OIDC tokens)
- Kerberos authentication for CERN services
- PIDCalib2 jobs requiring CERN Grid access
- Data access requiring authorization

The monitor catches all these scenarios and provides appropriate guidance.

## Best Practices

1. **Start Monitor First**: Always start the monitoring script before your DDmisID workflow
2. **Keep Visible**: Position the monitoring terminal where you can see authentication prompts
3. **Multiple Sessions**: Use the monitor for multiple DDmisID sessions
4. **No Interference**: The monitor only reads log files and doesn't interfere with your workflow

## Troubleshooting

### Monitor Not Detecting Prompts
- Ensure `watchdog` is installed: `pip install watchdog`
- Check if log directories exist and are being written to
- Verify the monitor is running with appropriate permissions

### Authentication Still Failing
- Complete the authentication steps shown in the monitor
- Check that tokens are properly saved in `~/.cache/cern-oidc/`
- Ensure your CERN credentials are valid

### Missing Dependencies
```bash
pip install watchdog
```

## Files

- `watch_auth_prompts.py` - Main monitoring script
- `test_auth_monitoring.py` - Test script for verification
- `requirements-auth-monitoring.txt` - Required dependencies
- `AUTH_MONITORING.md` - This documentation