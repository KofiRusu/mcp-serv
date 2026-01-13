#!/bin/bash
# ChatOS Remote Access Setup Script
# This script helps configure the system for remote access with Caddy reverse proxy

set -e

CHATOS_DIR="${CHATOS_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
CADDYFILE_PATH="/etc/caddy/Caddyfile"
CADDYFILE_SOURCE="$CHATOS_DIR/Caddyfile"

echo "🚀 ChatOS Remote Access Setup"
echo "=============================="
echo ""

# Check if running as root for Caddy setup
if [ "$EUID" -ne 0 ]; then 
    echo "⚠️  Some steps require sudo. You may need to run parts of this script with sudo."
    echo ""
fi

# Step 1: Check Caddy installation
echo "📦 Step 1: Checking Caddy installation..."
if command -v caddy &> /dev/null; then
    echo "✅ Caddy is installed: $(caddy version)"
else
    echo "❌ Caddy is not installed"
    echo "   Install with: sudo apt update && sudo apt install -y caddy"
    exit 1
fi

# Step 2: Copy Caddyfile
echo ""
echo "📝 Step 2: Setting up Caddyfile..."
if [ -f "$CADDYFILE_SOURCE" ]; then
    echo "   Source file found: $CADDYFILE_SOURCE"
    if [ "$EUID" -eq 0 ]; then
        cp "$CADDYFILE_SOURCE" "$CADDYFILE_PATH"
        echo "✅ Caddyfile copied to $CADDYFILE_PATH"
        echo "   ⚠️  IMPORTANT: Edit $CADDYFILE_PATH and replace 'chatos.yourdomain.com' with your domain!"
    else
        echo "   Run this to copy Caddyfile:"
        echo "   sudo cp $CADDYFILE_SOURCE $CADDYFILE_PATH"
        echo "   sudo nano $CADDYFILE_PATH  # Edit domain name"
    fi
else
    echo "❌ Caddyfile source not found: $CADDYFILE_SOURCE"
    exit 1
fi

# Step 3: Validate Caddyfile
echo ""
echo "🔍 Step 3: Validating Caddyfile..."
if [ "$EUID" -eq 0 ] && [ -f "$CADDYFILE_PATH" ]; then
    if caddy validate --config "$CADDYFILE_PATH" 2>/dev/null; then
        echo "✅ Caddyfile is valid"
    else
        echo "❌ Caddyfile validation failed"
        echo "   Check the configuration: sudo caddy validate --config $CADDYFILE_PATH"
    fi
else
    echo "   Run this to validate: sudo caddy validate --config $CADDYFILE_PATH"
fi

# Step 4: Configure firewall
echo ""
echo "🔥 Step 4: Firewall configuration..."
if command -v ufw &> /dev/null; then
    echo "   Recommended firewall rules:"
    echo "   sudo ufw allow 443/tcp"
    echo "   sudo ufw deny 3000/tcp"
    echo "   sudo ufw deny 8000/tcp"
    echo "   sudo ufw status"
else
    echo "   UFW not found. Configure your firewall manually:"
    echo "   - Allow port 443 (HTTPS)"
    echo "   - Block ports 3000 and 8000 from public access"
fi

# Step 5: Environment variables for backend
echo ""
echo "⚙️  Step 5: Backend environment configuration..."
echo "   The backend needs REALTIME_DATA_DIR to match scraper output:"
echo ""
echo "   Option 1: Set environment variable (recommended)"
echo "   export REALTIME_DATA_DIR=\"$CHATOS_DIR/sandbox-ui/data/realtime\""
echo ""
echo "   Option 2: Point to scraper data directories"
echo "   export REALTIME_DATA_DIR=\"$CHATOS_DIR/sandbox-ui/data\""
echo ""
echo "   Add to your backend startup script or systemd service."

# Step 6: Start services
echo ""
echo "🎯 Step 6: Starting services..."
if [ "$EUID" -eq 0 ]; then
    systemctl restart caddy
    systemctl enable caddy
    echo "✅ Caddy service restarted and enabled"
else
    echo "   Run this to start Caddy:"
    echo "   sudo systemctl restart caddy"
    echo "   sudo systemctl enable caddy"
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "📋 Next steps:"
echo "   1. Edit $CADDYFILE_PATH and set your domain name"
echo "   2. Ensure DNS A record points to this server"
echo "   3. Start backend: cd $CHATOS_DIR && python -m uvicorn ChatOS.app:app --host 0.0.0.0 --port 8000"
echo "   4. Start frontend: cd $CHATOS_DIR/sandbox-ui && npm run build && npm start"
echo "   5. Start scrapers: cd $CHATOS_DIR/scrapers && docker-compose -f docker-compose.scrapers.yml up -d"
echo "   6. Test: curl -k https://yourdomain.com/api/v1/realtime/dashboard"
echo ""
echo "🔍 Validation commands:"
echo "   - Check Caddy: sudo systemctl status caddy"
echo "   - Check API: curl http://localhost:8000/api/health"
echo "   - Check through proxy: curl -k https://yourdomain.com/api/health"
echo ""
