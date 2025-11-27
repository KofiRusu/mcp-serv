#!/bin/bash
# =============================================================================
# ChatOS Development Server
# 
# This script sets up the environment and runs the development server.
# Usage: ./run.sh
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🚀 ChatOS Development Server"
echo "=============================="

# Check for Python 3
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed."
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
echo "✓ Found Python $PYTHON_VERSION"

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source .venv/bin/activate

# Install/upgrade pip
pip install --upgrade pip --quiet

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r ChatOS/requirements.txt --quiet

echo ""
echo "=============================="
echo "✅ Environment ready!"
echo "🌐 Starting server at http://127.0.0.1:8000"
echo "📖 API docs at http://127.0.0.1:8000/docs"
echo "⏹️  Press Ctrl+C to stop"
echo "=============================="
echo ""

# Run the development server
uvicorn ChatOS.app:app --reload --host 127.0.0.1 --port 8000

