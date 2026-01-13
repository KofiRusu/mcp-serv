#!/bin/bash
# =============================================================================
# ChatOS Firewall Configuration Script
# =============================================================================
#
# This script configures UFW (Uncomplicated Firewall) for secure remote access.
# 
# What it does:
#   - Allows SSH (port 22) - keeps you from getting locked out!
#   - Allows HTTPS (port 443) - for Caddy reverse proxy
#   - Blocks direct access to frontend (port 3000)
#   - Blocks direct access to backend (port 8000)
#   - Enables the firewall
#
# Usage:
#   sudo bash scripts/configure-firewall.sh
#
# =============================================================================

set -e

echo "========================================"
echo "ChatOS Firewall Configuration"
echo "========================================"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "ERROR: This script must be run with sudo"
    echo "Usage: sudo bash $0"
    exit 1
fi

# Check if UFW is installed
if ! command -v ufw &> /dev/null; then
    echo "ERROR: UFW is not installed"
    echo "Install with: sudo apt install ufw"
    exit 1
fi

# Safety check - make sure SSH is allowed first
echo "Step 1: Ensuring SSH access (port 22)..."
ufw allow 22/tcp comment "SSH"
echo "   SSH allowed"

# Allow HTTPS
echo "Step 2: Allowing HTTPS (port 443)..."
ufw allow 443/tcp comment "HTTPS (Caddy)"
echo "   HTTPS allowed"

# Block direct frontend access
echo "Step 3: Blocking direct frontend access (port 3000)..."
ufw deny 3000/tcp comment "Block direct frontend"
echo "   Port 3000 blocked"

# Block direct backend access
echo "Step 4: Blocking direct backend access (port 8000)..."
ufw deny 8000/tcp comment "Block direct backend"
echo "   Port 8000 blocked"

# Also block Keycloak direct access if you want
# echo "Step 5: Blocking direct Keycloak access (port 8080)..."
# ufw deny 8080/tcp comment "Block direct Keycloak"
# echo "   Port 8080 blocked"

# Enable firewall
echo ""
echo "Step 5: Enabling firewall..."
echo "   (You'll still have SSH access, don't worry!)"
echo ""

# Only enable if not already enabled
if ufw status | grep -q "Status: inactive"; then
    # Enable without prompting
    echo "y" | ufw enable
    echo "   Firewall enabled!"
else
    echo "   Firewall was already enabled"
fi

echo ""
echo "========================================"
echo "Firewall Configuration Complete!"
echo "========================================"
echo ""

# Show status
echo "Current firewall status:"
echo ""
ufw status verbose

echo ""
echo "Summary:"
echo "  - SSH (22): ALLOWED - you can still connect"
echo "  - HTTPS (443): ALLOWED - Caddy serves the app"
echo "  - Frontend (3000): BLOCKED - must go through Caddy"
echo "  - Backend (8000): BLOCKED - must go through Caddy"
echo ""
echo "Your ChatOS is now accessible only through HTTPS!"
echo ""
echo "If you need to undo this, run:"
echo "  sudo ufw disable"
echo ""
