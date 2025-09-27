# Authentication Monitoring in DDmisID

## Problem Solved

Previously, when DDmisID executed PIDCalib2 jobs through Snakemake, authentication prompts would appear in subprocess log files where users couldn't see or interact with them. This led to jobs hanging while waiting for authentication that users weren't aware was needed.

## Solution

DDmisID now monitors subprocess output in real-time and surfaces authentication prompts to the main terminal, making them visible and actionable.

## How It Works

### 1. Real-time Output Monitoring
- The `_run_snakemake()` function now streams subprocess output
- Uses threading to monitor both stdout and stderr simultaneously  
- Pattern matching detects authentication-related messages

### 2. Authentication Prompt Detection
The system looks for these patterns in subprocess output:
```
- "CERN SINGLE SIGN-ON"
- "On your tablet, phone or computer, go to:"
- "https://auth.cern.ch/auth/realms/cern/device"
- "and enter the following code:"
- "You may also open the following link directly"
- "device?user_code="
- "Starting CERN OIDC device login"
- "OIDC authentication required"
```

### 3. User-Friendly Output
When authentication is detected, the system:
- Displays a prominent "🔐 AUTHENTICATION REQUIRED 🔐" message
- Shows the authentication URL and code in the main terminal
- Provides clear guidance on next steps

## New CLI Commands

### `ddmisid-engine auth`
Perform CERN OIDC authentication manually:
```bash
ddmisid-engine auth
```

### `ddmisid-engine status`
Check configuration and authentication status:
```bash
ddmisid-engine status
```

## Usage Workflow

### Normal Operation
```bash
# 1. Build configuration
ddmisid-engine build

# 2. Run pipeline - authentication prompts will be surfaced if needed
ddmisid-engine run -- --cores 4

# 3. If authentication is required, complete it in browser
# 4. Re-run the command or run 'ddmisid-engine auth' to update tokens
```

### If Authentication Issues Occur
```bash
# Check status
ddmisid-engine status

# Manually authenticate if needed
ddmisid-engine auth

# Retry your original command
ddmisid-engine run -- --cores 4
```

## Enhanced Job Scripts

The generated bash scripts now:
- Include authentication tokens directly in the scripts
- Source token environment files as fallback
- Detect authentication prompts in PIDCalib2 output
- Display clear messages when authentication is required

## Benefits

1. **Visibility**: Authentication prompts are no longer hidden in log files
2. **Actionable**: Users can see exactly what URL to visit and what code to enter
3. **Guidance**: Clear instructions on how to proceed after authentication
4. **Robustness**: Multiple fallback mechanisms ensure tokens reach subprocesses
5. **Monitoring**: Real-time feedback on authentication status

## Example Output

When authentication is needed, you'll see:

```
🔐 AUTHENTICATION REQUIRED 🔐
From stdout: CERN SINGLE SIGN-ON
--------------------------------------------------
🔐 AUTHENTICATION REQUIRED 🔐
From stdout: On your tablet, phone or computer, go to:
--------------------------------------------------
🔐 AUTHENTICATION REQUIRED 🔐
From stdout: https://auth.cern.ch/auth/realms/cern/device
--------------------------------------------------
🔐 AUTHENTICATION REQUIRED 🔐
From stdout: and enter the following code: ABCD-EFGH
--------------------------------------------------

============================================================
🚨 AUTHENTICATION WAS REQUIRED DURING EXECUTION 🚨
Please check the authentication prompts above and
complete the authentication process in your browser.

After completing authentication, you have two options:
1. Run 'ddmisid-engine auth' to update your stored credentials
2. Or simply re-run your original command

The authentication URL and code should be visible above.
============================================================
```

This makes the authentication process transparent and user-friendly, eliminating the frustration of hidden authentication prompts.