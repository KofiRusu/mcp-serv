#!/bin/bash
# ChatOS v2.0 - Start Scrapers Only
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CHATOS_DIR="$(dirname "$SCRIPT_DIR")"

echo "📊 Starting ChatOS Scrapers (Docker)"
echo "====================================="

cd "$CHATOS_DIR/scrapers"

# Build and start scrapers
docker compose -f docker-compose.scrapers.yml up -d --build

echo ""
echo "Scraper Status:"
docker ps --filter "name=chatos-" --format "  {{.Names}}: {{.Status}}"
echo ""
echo "View logs: docker compose -f docker-compose.scrapers.yml logs -f"
