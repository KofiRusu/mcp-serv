#!/bin/bash
# =============================================================================
# ChatOS v2.0 - Linux Transform Functions
# =============================================================================
# OS-specific transforms for Linux systems.
# This file is sourced by translate_patch.sh when running on Linux.
# =============================================================================

# Source common functions
TRANSFORM_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$TRANSFORM_DIR/common.sh"

# =============================================================================
# Linux-Specific Configuration
# =============================================================================

# Default paths for Linux
LINUX_OLLAMA_HOST="http://localhost:11434"
LINUX_DOCKER_OLLAMA_HOST="http://localhost:11434"

# =============================================================================
# Transform Functions
# =============================================================================

# Transform .env.local file for Linux
transform_env_file() {
    local env_file="$1"
    
    if [ ! -f "$env_file" ]; then
        _log warning "Env file not found: $env_file"
        return 1
    fi
    
    _log info "Applying Linux transforms to: $env_file"
    
    # Set OLLAMA_HOST
    replace_config_value "$env_file" "OLLAMA_HOST" "$LINUX_OLLAMA_HOST"
    
    # Configure GPU settings if NVIDIA GPU present
    if has_nvidia_gpu; then
        _log info "NVIDIA GPU detected, enabling CUDA settings"
        uncomment_line "$env_file" "CUDA_VISIBLE_DEVICES"
        replace_config_value "$env_file" "CUDA_VISIBLE_DEVICES" "0"
        
        # Comment out MPS settings (Apple Silicon only)
        comment_line "$env_file" "PYTORCH_ENABLE_MPS_FALLBACK"
    else
        _log info "No NVIDIA GPU detected, using CPU mode"
        comment_line "$env_file" "CUDA_VISIBLE_DEVICES"
        comment_line "$env_file" "PYTORCH_ENABLE_MPS_FALLBACK"
    fi
    
    _log success "Linux env transforms applied"
}

# Main transform function called by translate_patch.sh
run_os_transforms() {
    local repo_root="$1"
    
    _log info "Running Linux-specific transforms..."
    
    # 1. Detect Linux distribution
    local distro="unknown"
    if [ -f /etc/os-release ]; then
        distro=$(grep "^ID=" /etc/os-release | cut -d= -f2 | tr -d '"')
        _log info "Linux distribution: $distro"
    fi
    
    # 2. Check for required system tools
    local tools=("python3" "node" "npm" "git" "curl")
    for tool in "${tools[@]}"; do
        if command -v "$tool" &> /dev/null; then
            _log info "$tool: $(which $tool)"
        else
            _log warning "$tool not found"
        fi
    done
    
    # 3. Check GPU status
    if has_nvidia_gpu; then
        local gpu_name
        gpu_name=$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -1)
        _log info "NVIDIA GPU: $gpu_name"
        
        # Check CUDA version
        local cuda_version
        cuda_version=$(nvidia-smi --query-gpu=driver_version --format=csv,noheader 2>/dev/null | head -1)
        _log info "NVIDIA Driver: $cuda_version"
    else
        _log info "No NVIDIA GPU detected (CPU mode)"
    fi
    
    # 4. Check Ollama
    if command -v ollama &> /dev/null; then
        _log info "Ollama installed"
        
        # Check if Ollama is running
        if curl -s "$LINUX_OLLAMA_HOST" &> /dev/null; then
            _log info "Ollama is running at $LINUX_OLLAMA_HOST"
        else
            _log warning "Ollama is installed but not running"
            _log info "Start with: ollama serve"
        fi
    else
        _log warning "Ollama not installed"
        _log info "Install from: https://ollama.ai"
    fi
    
    # 5. Check Python environment
    if [ -d "$repo_root/.venv" ]; then
        _log info "Python venv exists at $repo_root/.venv"
        
        # Check venv Python version
        if [ -f "$repo_root/.venv/bin/python3" ]; then
            local venv_python
            venv_python=$("$repo_root/.venv/bin/python3" --version 2>&1)
            _log info "Venv Python: $venv_python"
        fi
    else
        _log warning "Python venv not found - run install.sh first"
    fi
    
    # 6. Verify miniforge/conda if training is needed
    local miniforge_path="$HOME/miniforge3"
    if [ -d "$miniforge_path" ]; then
        _log info "Miniforge found at $miniforge_path"
        
        # Check for unsloth environment
        if [ -d "$miniforge_path/envs/unsloth_py311" ]; then
            _log info "Unsloth environment exists"
        else
            _log warning "Unsloth environment not found (needed for training)"
        fi
    else
        _log info "Miniforge not installed (optional, for training)"
    fi
    
    # 7. Check systemd services (if applicable)
    if command -v systemctl &> /dev/null; then
        # Check if ollama service exists
        if systemctl list-unit-files | grep -q ollama; then
            local ollama_status
            ollama_status=$(systemctl is-active ollama 2>/dev/null || echo "inactive")
            _log info "Ollama systemd service: $ollama_status"
        fi
    fi
    
    # 8. Check Docker (if installed)
    if command -v docker &> /dev/null; then
        _log info "Docker installed"
        
        if docker info &> /dev/null; then
            _log info "Docker daemon is running"
        else
            _log warning "Docker daemon not running (or requires sudo)"
        fi
    fi
    
    _log success "Linux transforms complete"
}

# =============================================================================
# Helper Functions
# =============================================================================

# Get Linux distribution name
get_linux_distro() {
    if [ -f /etc/os-release ]; then
        grep "^ID=" /etc/os-release | cut -d= -f2 | tr -d '"'
    else
        echo "unknown"
    fi
}

# Get Linux kernel version
get_kernel_version() {
    uname -r
}

# Check if running on WSL
is_wsl() {
    grep -qi microsoft /proc/version 2>/dev/null || \
    grep -qi wsl /proc/version 2>/dev/null
}

# Install packages using appropriate package manager
install_packages() {
    local packages=("$@")
    local distro
    distro=$(get_linux_distro)
    
    case "$distro" in
        ubuntu|debian|kali)
            sudo apt-get update
            sudo apt-get install -y "${packages[@]}"
            ;;
        fedora)
            sudo dnf install -y "${packages[@]}"
            ;;
        arch|manjaro)
            sudo pacman -S --noconfirm "${packages[@]}"
            ;;
        *)
            _log error "Unknown distribution: $distro"
            return 1
            ;;
    esac
}

# =============================================================================
# Exports
# =============================================================================

export -f transform_env_file
export -f run_os_transforms
export -f get_linux_distro
export -f get_kernel_version
export -f is_wsl
export -f install_packages

