#!/usr/bin/env python3
"""
Debug script to check token validity and permissions.
"""

import boto3
import json
import base64
import time
from datetime import datetime

def decode_jwt(token):
    """Decode JWT token without verification."""
    try:
        parts = token.split('.')
        if len(parts) < 2:
            return None

        # Decode header
        header_payload = parts[0]
        header_payload += '=' * (4 - len(header_payload) % 4)
        header = json.loads(base64.urlsafe_b64decode(header_payload))

        # Decode payload
        payload_part = parts[1]
        payload_part += '=' * (4 - len(payload_part) % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_part))

        return {
            'header': header,
            'payload': payload
        }
    except Exception as e:
        print(f"Error decoding JWT: {e}")
        return None

def check_token_expiration(payload):
    """Check if token is expired."""
    exp = payload.get('exp', 0)
    iat = payload.get('iat', 0)
    current = int(time.time())

    print(f"\nToken Timing:")
    print(f"  Issued At: {datetime.fromtimestamp(iat)} ({iat})")
    print(f"  Expires At: {datetime.fromtimestamp(exp)} ({exp})")
    print(f"  Current Time: {datetime.fromtimestamp(current)} ({current})")

    if current >= exp:
        remaining = 0
        print(f"  Status: ❌ EXPIRED ({(current - exp) // 60} minutes ago)")
        return False
    else:
        remaining = exp - current
        print(f"  Status: ✅ VALID (expires in {remaining // 60} minutes)")
        return True

def main():
    print("=" * 70)
    print("Token Debug Tool")
    print("=" * 70)

    # Fetch token from Secrets Manager
    try:
        secrets_client = boto3.client('secretsmanager', region_name='us-east-1')
        secret = secrets_client.get_secret_value(
            SecretId='/agent/oran_agent/cognito/credentials'
        )
        creds = json.loads(secret['SecretString'])

        print("\n✓ Successfully fetched credentials from Secrets Manager")
        print(f"\nSecret Contents:")
        print(f"  - pool_id: {creds.get('pool_id')}")
        print(f"  - client_id: {creds.get('client_id')}")
        print(f"  - bearer_token: {'Present' if 'bearer_token' in creds else 'Missing'}")
        print(f"  - discovery_url: {creds.get('discovery_url')}")

        if 'bearer_token' not in creds:
            print("\n❌ No bearer_token found in secret!")
            return

        token = creds['bearer_token']

        # Decode token
        print("\n" + "=" * 70)
        print("Decoding JWT Token")
        print("=" * 70)

        decoded = decode_jwt(token)
        if not decoded:
            print("❌ Failed to decode token")
            return

        print("\nToken Header:")
        print(json.dumps(decoded['header'], indent=2))

        print("\nToken Payload:")
        print(json.dumps(decoded['payload'], indent=2))

        # Check expiration
        is_valid = check_token_expiration(decoded['payload'])

        # Check scopes
        print("\nToken Scopes:")
        scope = decoded['payload'].get('scope', '')
        scopes = scope.split() if scope else []
        for s in scopes:
            print(f"  - {s}")

        # Check user info
        print("\nUser Info:")
        print(f"  - Username: {decoded['payload'].get('username')}")
        print(f"  - Subject: {decoded['payload'].get('sub')}")
        print(f"  - Client ID: {decoded['payload'].get('client_id')}")

        # Recommendations
        print("\n" + "=" * 70)
        print("Recommendations")
        print("=" * 70)

        if not is_valid:
            print("\n❌ Token has EXPIRED. You need to:")
            print("   1. Regenerate a fresh token using your authentication method")
            print("   2. Update Secrets Manager with the new token:")
            print()
            print("   aws secretsmanager update-secret \\")
            print("     --secret-id '/agent/oran_agent/cognito/credentials' \\")
            print("     --secret-string '{\"pool_id\": \"...\", \"client_id\": \"...\", \"bearer_token\": \"NEW_TOKEN\"}'")
        else:
            print("\n✅ Token is valid!")
            print("\nIf you're still getting 403 errors, possible causes:")
            print("   1. Token doesn't have permission to invoke this specific agent")
            print("   2. Agent ARN in SSM might be incorrect")
            print("   3. Agent might not be deployed/active")
            print("   4. Additional authentication might be required")
            print("\nTo verify agent ARN:")
            print("   aws ssm get-parameter --name '/agent/oran_agent/runtime/agent_arn'")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
