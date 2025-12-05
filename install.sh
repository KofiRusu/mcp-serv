#!/bin/bash
# =============================================================================
# ChatOS v1.0 - Universal Installer
# Works on: Linux (x86_64, arm64) and macOS (Apple Silicon, Intel)
# =============================================================================
#
# Usage:
#   ./install.sh              # Full install (server + training)
#   ./install.sh --server     # Server only
#   ./install.sh --training   # Training only
#   ./install.sh --docker     # Docker setup only
#
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Detect platform
detect_platform() {
    OS="$(uname -s)"
    ARCH="$(uname -m)"
    
    case "$OS" in
        Linux*)     PLATFORM="linux";;
        Darwin*)    PLATFORM="macos";;
        *)          PLATFORM="unknown";;
    esac
    
    case "$ARCH" in
        x86_64)     ARCH_TYPE="x86_64";;
        arm64|aarch64) ARCH_TYPE="arm64";;
        *)          ARCH_TYPE="unknown";;
    esac
    
    echo -e "${CYAN}Detected: $PLATFORM ($ARCH_TYPE)${NC}"
}

# Print banner
print_banner() {
    echo -e "${CYAN}"
    echo "╔══════════════════════════════════════════════════════════╗"
    echo "║                   ChatOS v1.0 Installer                  ║"
    echo "║         AI Chat System with PersRM Training              ║"
    echo "╚══════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# Check prerequisites
check_prerequisites() {
    echo -e "${YELLOW}▶ Checking prerequisites...${NC}"
    
    # Check Python
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
        echo -e "  ${GREEN}✓${NC} Python $PYTHON_VERSION"
    else
        echo -e "  ${RED}✗${NC} Python 3 not found"
        echo "    Install: https://www.python.org/downloads/"
        exit 1
    fi
    
    # Check pip
    if command -v pip3 &> /dev/null || command -v pip &> /dev/null; then
        echo -e "  ${GREEN}✓${NC} pip installed"
    else
        echo -e "  ${RED}✗${NC} pip not found"
        exit 1
    fi
    
    # Check Docker (optional)
    if command -v docker &> /dev/null; then
        echo -e "  ${GREEN}✓${NC} Docker installed"
        DOCKER_AVAILABLE=true
    else
        echo -e "  ${YELLOW}○${NC} Docker not installed (optional)"
        DOCKER_AVAILABLE=false
    fi
    
    # Check GPU (Linux only)
    if [ "$PLATFORM" = "linux" ]; then
        if command -v nvidia-smi &> /dev/null; then
            GPU_NAME=$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -1)
            echo -e "  ${GREEN}✓${NC} NVIDIA GPU: $GPU_NAME"
            HAS_GPU=true
        else
            echo -e "  ${YELLOW}○${NC} No NVIDIA GPU detected (CPU training)"
            HAS_GPU=false
        fi
    fi
    
    # Check MPS (macOS Apple Silicon)
    if [ "$PLATFORM" = "macos" ] && [ "$ARCH_TYPE" = "arm64" ]; then
        echo -e "  ${GREEN}✓${NC} Apple Silicon detected (MPS acceleration)"
        HAS_MPS=true
    fi
}

# Create virtual environment
setup_venv() {
    echo -e "\n${YELLOW}▶ Setting up virtual environment...${NC}"
    
    if [ ! -d ".venv" ]; then
        python3 -m venv .venv
        echo -e "  ${GREEN}✓${NC} Created .venv"
    else
        echo -e "  ${GREEN}✓${NC} .venv exists"
    fi
    
    # Activate
    source .venv/bin/activate
    pip install --upgrade pip --quiet
    echo -e "  ${GREEN}✓${NC} Activated virtual environment"
}

# Install core dependencies
install_core() {
    echo -e "\n${YELLOW}▶ Installing core dependencies...${NC}"
    pip install -r ChatOS/requirements.txt --quiet
    echo -e "  ${GREEN}✓${NC} Core dependencies installed"
}

# Install PyTorch (platform-specific)
install_pytorch() {
    echo -e "\n${YELLOW}▶ Installing PyTorch...${NC}"
    
    if [ "$PLATFORM" = "macos" ]; then
        # macOS - MPS support
        pip install torch torchvision torchaudio --quiet
        echo -e "  ${GREEN}✓${NC} PyTorch installed (MPS support)"
    elif [ "$HAS_GPU" = true ]; then
        # Linux with NVIDIA GPU - CUDA support
        pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121 --quiet
        echo -e "  ${GREEN}✓${NC} PyTorch installed (CUDA 12.1)"
    else
        # Linux CPU only
        pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu --quiet
        echo -e "  ${GREEN}✓${NC} PyTorch installed (CPU)"
    fi
}

# Install training dependencies
install_training() {
    echo -e "\n${YELLOW}▶ Installing training dependencies...${NC}"
    pip install -r requirements-training.txt --quiet
    echo -e "  ${GREEN}✓${NC} Training dependencies installed"
}

# Setup directories
setup_directories() {
    echo -e "\n${YELLOW}▶ Setting up directories...${NC}"
    
    mkdir -p data/persrm
    mkdir -p models/persrm-continuous
    mkdir -p logs
    
    echo -e "  ${GREEN}✓${NC} Created data/, models/, logs/"
}

# Install CLI tools
install_cli() {
    echo -e "\n${YELLOW}▶ Installing CLI tools...${NC}"
    
    # Create bin directory
    mkdir -p "$HOME/bin"
    
    # Copy CLI tools
    if [ -f "bin/trading" ]; then
        cp bin/trading "$HOME/bin/trading"
        chmod +x "$HOME/bin/trading"
        echo -e "  ${GREEN}✓${NC} Installed 'trading' CLI"
    fi
    
    if [ -f "bin/hf-trading" ]; then
        cp bin/hf-trading "$HOME/bin/hf-trading"
        chmod +x "$HOME/bin/hf-trading"
        echo -e "  ${GREEN}✓${NC} Installed 'hf-trading' CLI"
    fi
    
    # Add to PATH if not already
    if [[ ":$PATH:" != *":$HOME/bin:"* ]]; then
        echo -e "  ${YELLOW}Note:${NC} Add to your shell config:"
        echo -e "    export PATH=\"\$HOME/bin:\$PATH\""
    fi
}

# Docker setup
setup_docker() {
    if [ "$DOCKER_AVAILABLE" = true ]; then
        echo -e "\n${YELLOW}▶ Setting up Docker...${NC}"
        
        # Build development image
        docker-compose build chatos
        echo -e "  ${GREEN}✓${NC} Docker images built"
        
        echo -e "\n  ${CYAN}Docker commands:${NC}"
        echo -e "    docker-compose up -d          # Start server"
        echo -e "    docker-compose up training    # Start GPU training"
        echo -e "    docker-compose up training-cpu # Start CPU training"
    fi
}

# Create sample training data
create_sample_data() {
    echo -e "\n${YELLOW}▶ Creating sample training data...${NC}"
    
    if [ ! -f "data/persrm/train.jsonl" ]; then
        cat > data/persrm/train.jsonl << 'EOF'
{"instruction": "What is machine learning?", "output": "Machine learning is a subset of artificial intelligence that enables systems to learn and improve from experience without being explicitly programmed.", "metadata": {"source": "sample", "quality": 0.9}}
{"instruction": "Explain neural networks", "output": "Neural networks are computing systems inspired by biological neural networks. They consist of interconnected nodes (neurons) organized in layers that process information and learn patterns from data.", "metadata": {"source": "sample", "quality": 0.9}}
{"instruction": "What is deep learning?", "output": "Deep learning is a subset of machine learning that uses neural networks with many layers (deep networks) to learn complex patterns in large amounts of data.", "metadata": {"source": "sample", "quality": 0.9}}
EOF
        echo -e "  ${GREEN}✓${NC} Created sample train.jsonl (3 examples)"
    else
        EXAMPLES=$(wc -l < data/persrm/train.jsonl)
        echo -e "  ${GREEN}✓${NC} train.jsonl exists ($EXAMPLES examples)"
    fi
    
    if [ ! -f "data/persrm/val.jsonl" ]; then
        cat > data/persrm/val.jsonl << 'EOF'
{"instruction": "What is reinforcement learning?", "output": "Reinforcement learning is a type of machine learning where an agent learns to make decisions by performing actions in an environment and receiving rewards or penalties.", "metadata": {"source": "sample", "quality": 0.9}}
EOF
        echo -e "  ${GREEN}✓${NC} Created sample val.jsonl"
    fi
}

# Print completion message
print_complete() {
    echo -e "\n${GREEN}════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}✅ ChatOS v1.0 Installation Complete!${NC}"
    echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "${CYAN}Quick Start:${NC}"
    echo -e "  ${YELLOW}1. Start the server:${NC}"
    echo -e "     ./run.sh"
    echo -e "     # or: docker-compose up -d"
    echo ""
    echo -e "  ${YELLOW}2. Open in browser:${NC}"
    echo -e "     http://localhost:8000"
    echo ""
    echo -e "  ${YELLOW}3. Start PersRM training:${NC}"
    if [ "$HAS_GPU" = true ]; then
        echo -e "     python -u ChatOS/training/persrm_pytorch_trainer.py --epochs 100"
        echo -e "     # or: docker-compose up training"
    else
        echo -e "     python -u ChatOS/training/persrm_pytorch_trainer.py --epochs 100"
    fi
    echo ""
    echo -e "  ${YELLOW}4. CLI tools:${NC}"
    echo -e "     trading status    # Check all processes"
    echo -e "     trading start     # Start all processes"
    echo ""
    echo -e "${CYAN}Documentation:${NC} ./README.md"
    echo -e "${CYAN}Training docs:${NC} ./TRAINING.md"
    echo ""
}

# Main installation
main() {
    print_banner
    detect_platform
    
    # Parse arguments
    INSTALL_SERVER=true
    INSTALL_TRAINING=true
    INSTALL_DOCKER=false
    
    for arg in "$@"; do
        case $arg in
            --server)
                INSTALL_TRAINING=false
                ;;
            --training)
                INSTALL_SERVER=false
                ;;
            --docker)
                INSTALL_DOCKER=true
                INSTALL_SERVER=false
                INSTALL_TRAINING=false
                ;;
            --help)
                echo "Usage: ./install.sh [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  --server     Install server only"
                echo "  --training   Install training only"
                echo "  --docker     Docker setup only"
                echo "  --help       Show this help"
                exit 0
                ;;
        esac
    done
    
    check_prerequisites
    setup_venv
    
    if [ "$INSTALL_SERVER" = true ]; then
        install_core
    fi
    
    if [ "$INSTALL_TRAINING" = true ]; then
        install_pytorch
        install_training
    fi
    
    setup_directories
    create_sample_data
    install_cli
    
    if [ "$INSTALL_DOCKER" = true ] || [ "$DOCKER_AVAILABLE" = true ]; then
        setup_docker
    fi
    
    print_complete
}

# Run main
main "$@"

