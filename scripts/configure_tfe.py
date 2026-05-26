#!/usr/bin/env python3
"""
TFE Configuration Script

This script configures a Terraform Enterprise instance by:
1. Waiting for TFE to be available
2. Creating an initial admin user
3. Creating a test organization

Usage:
    python3 configure_tfe.py <tfe_fqdn> <email> <admin_user> <password>

Example:
    python3 configure_tfe.py tfe28.aws.munnep.com patrick@test.com admin Password#1
"""

# Import required standard library modules
import sys          # For system operations like exit codes
import time         # For sleep/delays and timing
import json         # For parsing JSON responses from TFE API
import re           # For regular expression pattern matching (email, password validation)
import argparse     # For parsing command-line arguments
import ssl          # For handling SSL/TLS connections (disabling certificate verification)
import urllib.request  # For making HTTP requests
import urllib.error    # For handling HTTP errors
import urllib.parse    # For URL parsing utilities
import socket       # For network socket operations and timeout handling
from typing import Optional, Dict, Any  # For type hints


# Custom exception classes for better error handling
class TFEConfigError(Exception):
    """Base exception for TFE configuration errors"""
    pass


class PasswordValidationError(TFEConfigError):
    """Exception raised for password validation failures"""
    pass


class TFEAPIError(TFEConfigError):
    """Exception raised for TFE API errors"""
    pass


def validate_password(password: str) -> None:
    """
    Validate password meets TFE requirements.
    
    TFE requires passwords to be strong with multiple character types.
    This function checks all requirements and provides clear error messages.
    
    Args:
        password: The password to validate
        
    Raises:
        PasswordValidationError: If password doesn't meet requirements
    """
    errors = []
    
    # Check minimum length (8 characters)
    if len(password) < 8:
        errors.append("Password must be at least 8 characters long")
    
    # Check for at least one uppercase letter (A-Z)
    if not re.search(r'[A-Z]', password):
        errors.append("Password must contain at least one uppercase letter")
    
    # Check for at least one lowercase letter (a-z)
    if not re.search(r'[a-z]', password):
        errors.append("Password must contain at least one lowercase letter")
    
    # Check for at least one digit (0-9)
    if not re.search(r'[0-9]', password):
        errors.append("Password must contain at least one digit")
    
    # Check for at least one special character
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        errors.append("Password must contain at least one special character")
    
    # If any validation failed, raise an error with all issues listed
    if errors:
        raise PasswordValidationError(
            "Password validation failed:\n  - " + "\n  - ".join(errors)
        )


def validate_email(email: str) -> None:
    """
    Validate email format using regex pattern.
    
    Checks that the email has a valid structure: username@domain.tld
    
    Args:
        email: The email address to validate
        
    Raises:
        TFEConfigError: If email format is invalid
    """
    # Regex pattern for basic email validation
    # Format: alphanumeric+special@domain.tld
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, email):
        raise TFEConfigError(f"Invalid email format: {email}")


def make_request(
    url: str,
    method: str = 'GET',
    data: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    timeout: int = 30,
    allow_redirects: bool = True
) -> tuple[int, str]:
    """
    Make an HTTP request with SSL verification disabled.
    
    This is a wrapper around urllib that handles:
    - SSL certificate verification (disabled for self-signed certs)
    - HTTP redirects
    - JSON data encoding
    - Error handling
    
    Args:
        url: The URL to request
        method: HTTP method (GET, POST, HEAD)
        data: Optional JSON data to send (will be encoded)
        headers: Optional HTTP headers
        timeout: Request timeout in seconds
        allow_redirects: Whether to follow redirects
        
    Returns:
        Tuple of (status_code, response_body)
        
    Raises:
        TFEAPIError: If request fails
    """
    # Create SSL context that doesn't verify certificates
    # This is needed because TFE often uses self-signed certificates
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False  # Don't verify hostname
    ssl_context.verify_mode = ssl.CERT_NONE  # Don't verify certificate
    
    # Prepare request headers
    if headers is None:
        headers = {}
    
    # Add User-Agent header if not present (some servers block requests without it)
    if 'User-Agent' not in headers:
        headers['User-Agent'] = 'Mozilla/5.0 (compatible; TFE-Config-Script/1.0)'
    
    # Convert Python dict to JSON string and encode to bytes if data provided
    request_data = None
    if data is not None:
        request_data = json.dumps(data).encode('utf-8')
        # Set Content-Type header if not already set
        if 'Content-Type' not in headers:
            headers['Content-Type'] = 'application/json'
    
    # Create custom URL opener that handles HTTPS and redirects
    if allow_redirects:
        # Build opener with SSL handler and redirect handler
        opener = urllib.request.build_opener(
            urllib.request.HTTPSHandler(context=ssl_context),
            urllib.request.HTTPRedirectHandler()
        )
    else:
        # Build opener with just SSL handler (no redirects)
        opener = urllib.request.build_opener(
            urllib.request.HTTPSHandler(context=ssl_context)
        )
    
    # Create the HTTP request object
    req = urllib.request.Request(
        url,
        data=request_data,
        headers=headers,
        method=method
    )
    
    try:
        # Open the URL and read the response
        with opener.open(req, timeout=timeout) as response:
            body = response.read().decode('utf-8')
            return response.status, body
    except urllib.error.HTTPError as e:
        # HTTPError is raised for non-2xx status codes
        # For HEAD requests, redirects (301, 302) are actually success
        if method == 'HEAD' and e.code in [301, 302]:
            return e.code, ''
        # For other errors, return the status code and body for handling
        body = e.read().decode('utf-8') if e.fp else ''
        return e.code, body
    except urllib.error.URLError as e:
        # URLError is raised for network-level errors (DNS, connection refused, etc.)
        raise TFEAPIError(f"Network error: {str(e.reason)}")
    except socket.timeout:
        # Socket timeout occurs when request takes too long
        raise TFEAPIError(f"Connection timeout after {timeout} seconds")
    except Exception as e:
        # Catch any other unexpected errors
        raise TFEAPIError(f"Request failed: {str(e)}")


def wait_for_tfe(hostname: str, timeout: int = 120, check_interval: int = 4) -> None:
    """
    Wait for TFE to be available.
    
    Args:
        hostname: The TFE hostname
        timeout: Maximum time to wait in seconds (default: 120)
        check_interval: Time between checks in seconds (default: 4)
        
    Raises:
        TFEConfigError: If TFE doesn't become available within timeout
    """
    url = f"https://{hostname}/admin"
    start_time = time.time()
    
    print(f"Waiting for TFE at {hostname} to be available...")
    
    while True:
        elapsed = time.time() - start_time
        if elapsed > timeout:
            raise TFEConfigError(
                f"Timeout: TFE did not become available within {timeout} seconds"
            )
        
        try:
            status, body = make_request(url, method='HEAD', timeout=10)
            # 403 means TFE is up but requires auth (which is expected for /admin)
            # 200, 301, 302 are also valid "up" responses
            if status in [200, 301, 302, 403]:
                print("✓ TFE is up and running")
                print("Continuing with configuration in 5 seconds...")
                time.sleep(5)
                return
        except TFEAPIError:
            pass
        
        print(f"TFE is not available yet (elapsed: {int(elapsed)}s). Waiting...")
        time.sleep(check_interval)


def get_initial_token(hostname: str) -> str:
    """
    Retrieve the initial activation token (IACT) from TFE.
    
    The IACT is a one-time token used to create the first admin user.
    This token is only available on a fresh TFE installation before
    any admin user has been created.
    
    Args:
        hostname: The TFE hostname
        
    Returns:
        The initial activation token (a string)
        
    Raises:
        TFEAPIError: If token retrieval fails
    """
    # Endpoint to retrieve the initial admin creation token
    url = f"https://{hostname}/admin/retrieve-iact"
    
    print("Getting the initial activation token...")
    
    try:
        # Make GET request to retrieve the token
        status, body = make_request(url, timeout=30)
        
        # Remove any whitespace from the response
        token = body.strip()
        
        # Validate the token format
        # A valid IACT should be a long alphanumeric string without spaces or special chars
        # If it contains "error", spaces, or HTML tags, it's not a valid token
        if not token or len(token) < 10 or ' ' in token or 'error' in token.lower() or '<' in token:
            # Provide helpful error message based on what we received
            if 'error code: 1010' in token:
                raise TFEAPIError(
                    "Failed to retrieve activation token.\n"
                    "Received Cloudflare error 1010 (Access Denied).\n"
                    "This usually means:\n"
                    "  1. The TFE instance is behind Cloudflare protection\n"
                    "  2. Your IP or request is being blocked\n"
                    "  3. The /admin/retrieve-iact endpoint may not be accessible\n"
                    "Please check:\n"
                    "  - Cloudflare firewall rules\n"
                    "  - IP allowlist settings\n"
                    "  - Try accessing https://tfe3.munnep.com/admin/retrieve-iact in a browser"
                )
            elif status == 403:
                raise TFEAPIError(
                    "Failed to retrieve activation token (status 403).\n"
                    "This usually means the initial admin user has already been created.\n"
                    "The IACT (Initial Admin Creation Token) is only available on fresh TFE installations."
                )
            else:
                raise TFEAPIError(
                    f"Failed to retrieve activation token (status {status}).\n"
                    f"Response received: {body[:200]}"  # Show first 200 chars of response
                )
        
        print("✓ Successfully retrieved activation token")
        return token
        
    except TFEAPIError:
        # Re-raise TFEAPIError as-is
        raise
    except Exception as e:
        # Wrap any other exceptions in TFEAPIError
        raise TFEAPIError(f"Failed to retrieve activation token: {str(e)}")


def create_admin_user(
    hostname: str,
    username: str,
    email: str,
    password: str,
    initial_token: str
) -> str:
    """
    Create the initial admin user and retrieve the API token.
    
    This uses the IACT (Initial Admin Creation Token) to create the first
    admin user on a fresh TFE installation. The response includes an API
    token that can be used for subsequent API calls.
    
    Args:
        hostname: The TFE hostname
        username: Admin username (e.g., "admin")
        email: Admin email address
        password: Admin password (must meet complexity requirements)
        initial_token: Initial activation token from get_initial_token()
        
    Returns:
        The admin user's API token (used for subsequent API calls)
        
    Raises:
        TFEAPIError: If user creation fails
    """
    # Construct URL with the IACT token as a query parameter
    url = f"https://{hostname}/admin/initial-admin-user?token={initial_token}"
    
    print(f"Creating admin user '{username}'...")
    
    # Prepare the JSON payload with user details
    payload = {
        "username": username,
        "email": email,
        "password": password
    }
    
    # Set headers for JSON request
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        # Make POST request to create the admin user
        status, body = make_request(url, method='POST', data=payload, headers=headers, timeout=30)
        
        # Check for validation errors (422 = Unprocessable Entity)
        if status == 422:
            try:
                # Parse error response to get detailed error message
                error_data = json.loads(body)
                error_msg = error_data.get('errors', [{}])[0].get('detail', 'Unknown error')
                raise TFEAPIError(f"User creation failed: {error_msg}")
            except (json.JSONDecodeError, KeyError, IndexError):
                # If we can't parse the error, just report the status code
                raise TFEAPIError(f"User creation failed with status {status}")
        
        # Check for other non-success status codes
        if status != 200:
            raise TFEAPIError(f"User creation failed with status {status}")
        
        try:
            # Parse the JSON response
            data = json.loads(body)
            # Extract the API token from the response
            token = data.get('token')
            
            # Verify we got a token
            if not token:
                raise TFEAPIError("No token returned in admin user creation response")
            
            print(f"✓ Successfully created admin user '{username}'")
            return token
        except json.JSONDecodeError:
            raise TFEAPIError("Failed to parse admin user creation response")
        
    except TFEAPIError:
        # Re-raise TFEAPIError as-is
        raise
    except Exception as e:
        # Wrap any other exceptions in TFEAPIError
        raise TFEAPIError(f"Failed to create admin user: {str(e)}")


def create_organization(
    hostname: str,
    org_name: str,
    email: str,
    token: str
) -> Dict[str, Any]:
    """
    Create an organization in TFE.
    
    Organizations are workspaces containers in TFE. This function creates
    a new organization using the TFE API v2 with the admin user's token.
    
    Args:
        hostname: The TFE hostname
        org_name: Organization name (e.g., "test", "production")
        email: Organization email (for notifications)
        token: Admin API token (from create_admin_user)
        
    Returns:
        The organization creation response data (dict)
        
    Raises:
        TFEAPIError: If organization creation fails
    """
    # TFE API v2 endpoint for organizations
    url = f"https://{hostname}/api/v2/organizations"
    
    print(f"Creating organization '{org_name}'...")
    
    # Prepare JSON:API formatted payload
    # TFE uses JSON:API specification for its API
    payload = {
        "data": {
            "type": "organizations",  # Resource type
            "attributes": {
                "name": org_name,
                "email": email
            }
        }
    }
    
    # Set headers with Bearer token authentication
    headers = {
        "Authorization": f"Bearer {token}",  # Use admin token for auth
        "Content-Type": "application/vnd.api+json"  # JSON:API content type
    }
    
    try:
        # Make POST request to create organization
        status, body = make_request(url, method='POST', data=payload, headers=headers, timeout=30)
        
        # Check for validation errors (422 = Unprocessable Entity)
        if status == 422:
            try:
                # Parse error response
                error_data = json.loads(body)
                errors = error_data.get('errors', [])
                if errors:
                    error_detail = errors[0].get('detail', 'Unknown error')
                    # Check if organization already exists (common error)
                    if 'already exists' in error_detail.lower() or 'has already been taken' in error_detail.lower():
                        raise TFEAPIError(
                            f"Organization '{org_name}' already exists. "
                            "Please use a different organization name or delete the existing one."
                        )
                    raise TFEAPIError(f"Organization creation failed: {error_detail}")
            except (json.JSONDecodeError, KeyError, IndexError):
                # If we can't parse the error, just report the status code
                raise TFEAPIError(f"Organization creation failed with status {status}")
        
        # Check for success (200 or 201 are both valid for creation)
        if status not in [200, 201]:
            raise TFEAPIError(f"Organization creation failed with status {status}")
        
        try:
            # Parse the JSON response
            data = json.loads(body)
            print(f"✓ Successfully created organization '{org_name}'")
            return data
        except json.JSONDecodeError:
            raise TFEAPIError("Failed to parse organization creation response")
        
    except TFEAPIError:
        # Re-raise TFEAPIError as-is
        raise
    except Exception as e:
        # Wrap any other exceptions in TFEAPIError
        raise TFEAPIError(f"Failed to create organization: {str(e)}")


def parse_arguments() -> argparse.Namespace:
    """
    Parse command line arguments using argparse.
    
    This function defines all the command-line arguments the script accepts
    and validates them (e.g., ensuring timeout is an integer).
    
    Returns:
        Parsed arguments as a Namespace object
    """
    # Create argument parser with description and help text
    parser = argparse.ArgumentParser(
        description='Configure Terraform Enterprise instance',
        formatter_class=argparse.RawDescriptionHelpFormatter,  # Preserve formatting in epilog
        epilog="""
Example:
    python3 configure_tfe.py tfe28.aws.munnep.com patrick@test.com admin Password#1

Password Requirements:
    - At least 8 characters long
    - Contains at least one uppercase letter
    - Contains at least one lowercase letter
    - Contains at least one digit
    - Contains at least one special character
        """
    )
    
    # Define required positional arguments
    parser.add_argument('hostname', help='TFE hostname (FQDN)')
    parser.add_argument('email', help='Admin user email address')
    parser.add_argument('username', help='Admin username')
    parser.add_argument('password', help='Admin user password')
    
    # Define optional arguments with defaults
    parser.add_argument(
        '--org-name',
        default='test',
        help='Organization name to create (default: test)'
    )
    parser.add_argument(
        '--timeout',
        type=int,  # Ensure value is converted to integer
        default=120,
        help='Timeout in seconds to wait for TFE (default: 120)'
    )
    
    # Parse and return arguments
    return parser.parse_args()


def main() -> int:
    """
    Main function to configure TFE.
    
    This orchestrates the entire TFE configuration process:
    1. Parse command-line arguments
    2. Validate inputs (email format, password strength)
    3. Wait for TFE to be available
    4. Get initial activation token
    5. Create admin user
    6. Create organization
    
    Returns:
        Exit code (0 for success, 1 for failure)
    """
    try:
        # Step 1: Parse command-line arguments
        args = parse_arguments()
        
        # Print banner with configuration details
        print("=" * 80)
        print("TFE Configuration Script")
        print("=" * 80)
        print(f"Hostname: {args.hostname}")
        print(f"Email: {args.email}")
        print(f"Username: {args.username}")
        print(f"Organization: {args.org_name}")
        print("=" * 80)
        print()
        
        # Step 2: Validate inputs before making any API calls
        print("Validating inputs...")
        validate_email(args.email)  # Check email format
        validate_password(args.password)  # Check password meets requirements
        print("✓ Input validation passed")
        print()
        
        # Step 3: Wait for TFE to be available (may take time after startup)
        wait_for_tfe(args.hostname, timeout=args.timeout)
        print()
        
        # Step 4: Get the initial activation token (IACT)
        # This token is only available on fresh TFE installations
        initial_token = get_initial_token(args.hostname)
        print()
        
        # Step 5: Create the admin user using the IACT
        # This returns an API token we can use for subsequent calls
        admin_token = create_admin_user(
            args.hostname,
            args.username,
            args.email,
            args.password,
            initial_token
        )
        print()
        
        # Step 6: Create an organization using the admin token
        create_organization(
            args.hostname,
            args.org_name,
            args.email,
            admin_token
        )
        print()
        
        # Success! Print completion message
        print("=" * 80)
        print("✓ Script completed successfully!")
        print("=" * 80)
        return 0  # Exit code 0 = success
        
    except PasswordValidationError as e:
        # Handle password validation errors specifically
        print(f"\n❌ ERROR: {str(e)}", file=sys.stderr)
        return 1  # Exit code 1 = failure
    except TFEConfigError as e:
        # Handle TFE configuration errors (API errors, timeouts, etc.)
        print(f"\n❌ ERROR: {str(e)}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        # Handle Ctrl+C gracefully
        print("\n\n⚠ Script interrupted by user", file=sys.stderr)
        return 1
    except Exception as e:
        # Catch any unexpected errors and print stack trace
        print(f"\n❌ UNEXPECTED ERROR: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


# Entry point: run main() when script is executed directly
if __name__ == "__main__":
    sys.exit(main())  # Exit with the return code from main()

# Made with Bob
