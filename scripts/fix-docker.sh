#!/bin/bash
# =============================================================================
# Fix Docker Symlink Script
# =============================================================================
# The Docker data directory was symlinked to a LUKS-encrypted drive that may
# not be mounted. This script fixes it by pointing to local storage.
#
# Usage: sudo ./scripts/fix-docker.sh
# =============================================================================

set -e

DOCKER_DATA="/home/kr/docker-data"
DOCKER_LIB="/var/lib/docker"

echo "=== Docker Symlink Fix Script ==="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "ERROR: This script must be run as root (sudo)"
    echo "Usage: sudo $0"
    exit 1
fi

# Create local Docker data directory
echo "Creating local Docker data directory: $DOCKER_DATA"
mkdir -p "$DOCKER_DATA"
chown root:root "$DOCKER_DATA"

# Stop Docker
echo "Stopping Docker..."
systemctl stop docker.socket 2>/dev/null || true
systemctl stop docker 2>/dev/null || true
sleep 2

# Remove old symlink/directory
echo "Removing old Docker lib path..."
if [ -L "$DOCKER_LIB" ]; then
    rm -f "$DOCKER_LIB"
elif [ -d "$DOCKER_LIB" ]; then
    # If it's a real directory with data, move it
    if [ "$(ls -A $DOCKER_LIB 2>/dev/null)" ]; then
        echo "Moving existing Docker data to $DOCKER_DATA..."
        mv "$DOCKER_LIB"/* "$DOCKER_DATA"/ 2>/dev/null || true
    fi
    rm -rf "$DOCKER_LIB"
fi

# Create new symlink
echo "Creating symlink: $DOCKER_LIB -> $DOCKER_DATA"
ln -sf "$DOCKER_DATA" "$DOCKER_LIB"

# Start Docker
echo "Starting Docker..."
systemctl start docker

# Wait for Docker to be ready
echo "Waiting for Docker to be ready..."
sleep 3

# Verify
if docker info >/dev/null 2>&1; then
    echo ""
    echo "=== SUCCESS ==="
    echo "Docker is now running with local storage at: $DOCKER_DATA"
    echo ""
    echo "To start the scrapers:"
    echo "  cd /home/kr/ChatOS-v2.0/scrapers"
    echo "  docker-compose -f docker-compose.scrapers.yml up -d"
else
    echo ""
    echo "=== WARNING ==="
    echo "Docker may not have started correctly. Check with:"
    echo "  systemctl status docker"
    echo "  journalctl -u docker -n 50"
fi

