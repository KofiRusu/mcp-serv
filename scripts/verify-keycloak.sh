#!/bin/bash
# =============================================================================
# ChatOS Keycloak Verification Script
# =============================================================================
#
# This script checks if Keycloak is properly configured for ChatOS.
#
# Usage:
#   bash scripts/verify-keycloak.sh
#
# =============================================================================

echo "=================================================="
echo "ChatOS Keycloak Verification"
echo "=================================================="
echo ""

# Default Keycloak settings
KEYCLOAK_URL="${KEYCLOAK_URL:-http://localhost:8080}"
KEYCLOAK_REALM="${KEYCLOAK_REALM:-chatos}"
KEYCLOAK_CLIENT_ID="${KEYCLOAK_CLIENT_ID:-chatos-app}"

echo "Configuration:"
echo "  KEYCLOAK_URL:       $KEYCLOAK_URL"
echo "  KEYCLOAK_REALM:     $KEYCLOAK_REALM"
echo "  KEYCLOAK_CLIENT_ID: $KEYCLOAK_CLIENT_ID"
echo ""

# Test 1: Check if Keycloak is reachable
echo "[1/4] Checking if Keycloak is reachable..."
if curl -s -o /dev/null -w "%{http_code}" "$KEYCLOAK_URL" | grep -q "200\|302\|301"; then
    echo "  ✓ Keycloak is reachable"
else
    echo "  ✗ Cannot reach Keycloak at $KEYCLOAK_URL"
    echo ""
    echo "  Make sure Keycloak is running:"
    echo "    docker run -d --name keycloak -p 8080:8080 \\"
    echo "      -e KEYCLOAK_ADMIN=admin \\"
    echo "      -e KEYCLOAK_ADMIN_PASSWORD=admin \\"
    echo "      quay.io/keycloak/keycloak:latest start-dev"
    echo ""
fi

# Test 2: Check realm exists
echo ""
echo "[2/4] Checking if realm '$KEYCLOAK_REALM' exists..."
REALM_CHECK=$(curl -s "$KEYCLOAK_URL/realms/$KEYCLOAK_REALM/.well-known/openid-configuration")
if echo "$REALM_CHECK" | grep -q "issuer"; then
    echo "  ✓ Realm '$KEYCLOAK_REALM' exists"
else
    echo "  ✗ Realm '$KEYCLOAK_REALM' not found"
    echo ""
    echo "  Create the realm in Keycloak Admin Console:"
    echo "    1. Go to $KEYCLOAK_URL/admin"
    echo "    2. Create realm named '$KEYCLOAK_REALM'"
fi

# Test 3: Check OIDC endpoints
echo ""
echo "[3/4] Checking OpenID Connect endpoints..."
OIDC_CONFIG="$KEYCLOAK_URL/realms/$KEYCLOAK_REALM/.well-known/openid-configuration"
if curl -s "$OIDC_CONFIG" | grep -q "authorization_endpoint"; then
    echo "  ✓ OIDC configuration available"
    
    # Extract JWKS URL
    JWKS_URI=$(curl -s "$OIDC_CONFIG" | grep -o '"jwks_uri":"[^"]*"' | cut -d'"' -f4)
    if [ -n "$JWKS_URI" ]; then
        echo "  ✓ JWKS URI: $JWKS_URI"
    fi
else
    echo "  ✗ OIDC configuration not available"
fi

# Test 4: Environment variables check
echo ""
echo "[4/4] Checking environment variables..."
if [ -n "$KEYCLOAK_URL" ]; then
    echo "  ✓ KEYCLOAK_URL is set"
else
    echo "  ⚠ KEYCLOAK_URL not set (using default)"
fi

if [ -n "$KEYCLOAK_REALM" ]; then
    echo "  ✓ KEYCLOAK_REALM is set"
else
    echo "  ⚠ KEYCLOAK_REALM not set (using default)"
fi

if [ -n "$KEYCLOAK_CLIENT_ID" ]; then
    echo "  ✓ KEYCLOAK_CLIENT_ID is set"
else
    echo "  ⚠ KEYCLOAK_CLIENT_ID not set (using default)"
fi

echo ""
echo "=================================================="
echo "Keycloak Setup Guide"
echo "=================================================="
echo ""
echo "If Keycloak is not set up yet, follow these steps:"
echo ""
echo "1. Start Keycloak (if not running):"
echo "   docker run -d --name keycloak -p 8080:8080 \\"
echo "     -e KEYCLOAK_ADMIN=admin \\"
echo "     -e KEYCLOAK_ADMIN_PASSWORD=admin \\"
echo "     quay.io/keycloak/keycloak:latest start-dev"
echo ""
echo "2. Access Admin Console: $KEYCLOAK_URL/admin"
echo "   Username: admin"
echo "   Password: admin"
echo ""
echo "3. Create Realm:"
echo "   - Click 'Create Realm'"
echo "   - Name: $KEYCLOAK_REALM"
echo "   - Click 'Create'"
echo ""
echo "4. Create Client:"
echo "   - Go to Clients > Create client"
echo "   - Client ID: $KEYCLOAK_CLIENT_ID"
echo "   - Client type: OpenID Connect"
echo "   - Click 'Next'"
echo "   - Enable 'Client authentication': OFF (public client)"
echo "   - Enable 'Standard flow': ON"
echo "   - Click 'Next'"
echo "   - Root URL: https://your-domain.com"
echo "   - Valid redirect URIs: https://your-domain.com/*"
echo "   - Web origins: https://your-domain.com"
echo "   - Click 'Save'"
echo ""
echo "5. Create Admin User:"
echo "   - Go to Users > Add user"
echo "   - Username: your-username"
echo "   - Email: your-email"
echo "   - Click 'Create'"
echo "   - Go to Credentials tab"
echo "   - Set password"
echo "   - Go to Role mapping tab"
echo "   - Assign 'admin' role"
echo ""
echo "6. Update Caddyfile to proxy /auth/* to Keycloak:"
echo "   reverse_proxy /auth/* localhost:8080"
echo ""
echo "7. Set environment variables for ChatOS backend:"
echo "   export KEYCLOAK_URL=$KEYCLOAK_URL"
echo "   export KEYCLOAK_REALM=$KEYCLOAK_REALM"
echo "   export KEYCLOAK_CLIENT_ID=$KEYCLOAK_CLIENT_ID"
echo ""
echo "=================================================="
