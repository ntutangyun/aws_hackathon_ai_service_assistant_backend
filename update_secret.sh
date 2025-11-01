#!/bin/bash
# Update Secrets Manager to include username and password
aws secretsmanager update-secret \
  --secret-id "/agent/oran_agent/cognito/credentials" \
  --secret-string '{
    "pool_id": "us-east-1_DI4hhJrFI",
    "client_id": "13f9umnufmpo99dibc24751mfs",
    "username": "testuser",
    "password": "MyPassword123!",
    "discovery_url": "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_DI4hhJrFI/.well-known/openid-configuration"
  }'
echo "Secret updated with username and password"
