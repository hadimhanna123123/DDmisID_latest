# Authentication Monitoring Fix

## Problem
When running DDmisID with Snakemake, PIDCalib2 jobs would prompt for CERN authentication even after the user had already authenticated with `ddmisid-engine`. This happened because:

1. User authenticates once with OIDC device flow
2. Snakemake spawns subprocesses to run bash scripts
3. PIDCalib2 runs inside `lb-conda` environments that don't inherit authentication
4. User gets prompted to authenticate again for each job

## Solution
Implemented a simple **Authentication Monitor** that:

1. **Detects Authentication Prompts**: Uses regex patterns to identify CERN SSO prompts in subprocess output
2. **Pauses Execution**: When authentication is detected, pauses the process and prompts user
3. **Continues After Auth**: Once user completes authentication, continues normal execution
4. **Real-time Monitoring**: Shows all output in real-time while monitoring for auth prompts

## Key Components

### `ddmisid/utils/auth_monitor.py`
- `AuthenticationMonitor`: Class that detects auth prompts using regex patterns
- `run_with_auth_monitoring()`: Function to run any subprocess with auth monitoring
- `run_shell_with_auth_monitoring()`: Specialized function for bash scripts

### Updated `workflow/Snakefile`
- `extract_pid_effs` rule now uses auth monitoring instead of simple shell execution
- Real-time output display with authentication handling

### Simplified Job Scripts
- Removed complex token embedding approach
- Scripts are now simpler and rely on the monitoring system

## How It Works

1. **Start Command**: Snakemake starts a PIDCalib2 job via bash script
2. **Monitor Output**: Auth monitor reads output line-by-line in real-time
3. **Detect Auth Pattern**: When regex matches CERN SSO prompt, execution pauses
4. **User Prompt**: User is prompted to complete authentication in browser
5. **Continue**: After user presses ENTER, execution continues normally

## Regex Patterns
The monitor detects these authentication patterns:
- `CERN SINGLE SIGN-ON`
- `On your tablet, phone or computer, go to:`
- `https://auth.cern.ch/auth/realms/cern/device`
- `and enter the following code:`
- `You may also open the following link directly`
- `device?user_code=`

## Usage
Authentication monitoring is now automatic when running:
```bash
ddmisid-engine run -- --cores 4
```

When authentication is required:
1. **You'll see**: The CERN SSO prompt displayed
2. **System pauses**: "Press ENTER when authentication is complete..."
3. **You complete**: Authentication in browser as normal
4. **Press ENTER**: To continue execution
5. **Jobs continue**: Without further authentication prompts

## Benefits
- ✅ **Simple**: No complex token management
- ✅ **Reliable**: Works regardless of conda environment issues
- ✅ **User-friendly**: Clear prompts and real-time feedback
- ✅ **Robust**: Handles authentication at any point during execution
- ✅ **Maintainable**: Easy to understand and modify