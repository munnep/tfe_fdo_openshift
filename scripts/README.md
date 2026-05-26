# TFE Configuration Scripts

This directory contains scripts to configure Terraform Enterprise (TFE) instances.

## Python Script (Recommended)

### Installation

**No installation required!** The script uses only Python standard library modules, so it works out of the box with Python 3.6+.

Just make sure you have Python 3 installed:

```bash
python3 --version
```

### Usage

```bash
python3 configure_tfe.py <hostname> <email> <username> <password> [--org-name ORG] [--timeout SECONDS]
python3 configure_tfe.py tfe3.munnep.com patrick.munne@ibm.com admin Password#1
```

**Arguments:**
- `hostname`: TFE hostname (FQDN), e.g., `tfe28.aws.munnep.com`
- `email`: Admin user email address
- `username`: Admin username
- `password`: Admin user password

**Optional Arguments:**
- `--org-name`: Organization name to create (default: `test`)
- `--timeout`: Timeout in seconds to wait for TFE (default: `600`)

**Example:**

```bash
python3 configure_tfe.py tfe3.example.com example@example.com admin Password#1
```

### What the Script Does

The script performs the following steps automatically:

1. **Validates Inputs**: Checks email format and password strength before making any API calls
2. **Waits for TFE**: Polls the TFE instance until it's available (handles fresh installations)
3. **Retrieves IACT**: Gets the Initial Admin Creation Token (only available on fresh TFE)
4. **Creates Admin User**: Creates the first admin user with the provided credentials
5. **Creates Organization**: Sets up an initial organization for workspaces
6. **Reports Success**: Provides clear feedback at each step

### Password Requirements

The password must meet the following requirements:
- At least 8 characters long
- Contains at least one uppercase letter (A-Z)
- Contains at least one lowercase letter (a-z)
- Contains at least one digit (0-9)
- Contains at least one special character (!@#$%^&*(),.?":{}|<>)

**Example valid passwords:**
- `MyP@ssw0rd`
- `Secure123!`
- `Admin#2024`

### Error Handling

The Python script includes comprehensive error handling for common scenarios:

#### 1. Password Validation Errors
If the password doesn't meet requirements, you'll get a detailed error message:

```
❌ ERROR: Password validation failed:
  - Password must contain at least one uppercase letter
  - Password must contain at least one special character
```

**Solution**: Use a password that meets all requirements.

#### 2. Organization Already Exists
If the organization name is already taken:

```
❌ ERROR: Organization 'test' already exists. Please use a different organization name or delete the existing one.
```

**Solution**: Use `--org-name` to specify a different organization name.

#### 3. Email Validation
Invalid email formats are caught before making API calls:

```
❌ ERROR: Invalid email format: notanemail
```

**Solution**: Provide a valid email address (e.g., `user@example.com`).

#### 4. TFE Not Available
If TFE doesn't respond within the timeout period:

```
❌ ERROR: Timeout: TFE did not become available within 120 seconds
```

**Solution**: Increase timeout with `--timeout 300` or check if TFE is actually running.

#### 5. IACT Already Used
If the initial admin user has already been created:

```
❌ ERROR: Failed to retrieve activation token (status 403).
This usually means the initial admin user has already been created.
```

**Solution**: This script only works on fresh TFE installations. Use existing credentials or reset TFE.

#### 6. Cloudflare/Network Issues
The script handles Cloudflare protection and network errors gracefully with clear error messages.

### Features

- ✅ **Zero Dependencies**: Uses only Python standard library
- ✅ **Input Validation**: Validates email format and password strength before API calls
- ✅ **Comprehensive Error Handling**: Clear, actionable error messages for all failure scenarios
- ✅ **TFE Availability Check**: Waits for TFE to be ready before proceeding
- ✅ **SSL Support**: Handles self-signed certificates automatically
- ✅ **Cloudflare Compatible**: Works with Cloudflare-protected TFE instances
- ✅ **Progress Indicators**: Shows detailed status at each step (✓ for success)
- ✅ **Configurable**: Customize timeout and organization name via command-line flags
- ✅ **Interrupt Handling**: Gracefully handles Ctrl+C interruption
- ✅ **Exit Codes**: Returns 0 for success, 1 for failure (script-friendly)
- ✅ **Well Commented**: Extensive inline comments explaining each step

### Important Notes

1. **Fresh Installation Only**: This script only works on fresh TFE installations that haven't been configured yet. The IACT (Initial Admin Creation Token) is only available before the first admin user is created.

2. **One-Time Use**: After successfully running this script, the IACT endpoint will no longer be accessible. You'll need to use the admin credentials you created for future operations.

3. **Network Requirements**: The script needs network access to the TFE instance. If TFE is behind a firewall or VPN, ensure you have proper access.

4. **Cloudflare Protection**: The script includes a User-Agent header to work with Cloudflare-protected TFE instances.

