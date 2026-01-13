#!/bin/bash
# =============================================================================
# ChatOS v2.0 - macOS (Darwin) Transform Functions
# =============================================================================
# OS-specific transforms for macOS systems.
# This file is sourced by translate_patch.sh when running on macOS.
# =============================================================================

# Source common functions
TRANSFORM_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$TRANSFORM_DIR/common.sh"

# =============================================================================
# macOS-Specific Configuration
# =============================================================================

# Default paths for macOS
DARWIN_OLLAMA_HOST="http://localhost:11434"
DARWIN_DOCKER_OLLAMA_HOST="http://host.docker.internal:11434"

# Homebrew paths
HOMEBREW_PREFIX="${HOMEBREW_PREFIX:-/opt/homebrew}"
if [ ! -d "$HOMEBREW_PREFIX" ]; then
    HOMEBREW_PREFIX="/usr/local"  # Intel Mac fallback
fi

# =============================================================================
# Transform Functions
# =============================================================================

# Transform .env.local file for macOS
transform_env_file() {
    local env_file="$1"
    
    if [ ! -f "$env_file" ]; then
        _log warning "Env file not found: $env_file"
        return 1
    fi
    
    _log info "Applying macOS transforms to: $env_file"
    
    # Set OLLAMA_HOST
    if is_docker; then
        replace_config_value "$env_file" "OLLAMA_HOST" "$DARWIN_DOCKER_OLLAMA_HOST"
    else
        replace_config_value "$env_file" "OLLAMA_HOST" "$DARWIN_OLLAMA_HOST"
    fi
    
    # Enable MPS for Apple Silicon
    if has_mps; then
        _log info "Enabling MPS (Apple Silicon) support"
        uncomment_line "$env_file" "PYTORCH_ENABLE_MPS_FALLBACK"
        replace_config_value "$env_file" "PYTORCH_ENABLE_MPS_FALLBACK" "1"
        
        # Comment out CUDA settings
        comment_line "$env_file" "CUDA_VISIBLE_DEVICES"
    fi
    
    _log success "macOS env transforms applied"
}

# Main transform function called by translate_patch.sh
run_os_transforms() {
    local repo_root="$1"
    
    _log info "Running macOS-specific transforms..."
    
    # 1. Check Homebrew
    if command -v brew &> /dev/null; then
        _log info "Homebrew detected at: $(brew --prefix)"
    else
        _log warning "Homebrew not found - some features may not work"
    fi
    
    # 2. Check for common macOS tools
    local tools=("python3" "node" "npm")
    for tool in "${tools[@]}"; do
        if command -v "$tool" &> /dev/null; then
            _log info "$tool: $(which $tool)"
        else
            _log warning "$tool not found"
        fi
    done
    
    # 3. Handle sed differences (BSD vs GNU)
    # macOS uses BSD sed which has different syntax
    # Our scripts already handle this with the .bak pattern
    
    # 4. Check Ollama
    if command -v ollama &> /dev/null; then
        _log info "Ollama installed"
        
        # Check if Ollama is running
        if curl -s "$DARWIN_OLLAMA_HOST" &> /dev/null; then
            _log info "Ollama is running at $DARWIN_OLLAMA_HOST"
        else
            _log warning "Ollama is installed but not running"
            _log info "Start with: ollama serve"
        fi
    else
        _log warning "Ollama not installed"
        _log info "Install with: brew install ollama"
    fi
    
    # 5. Handle file permission differences
    # macOS may strip executable bits on some operations
    # This is handled by the main translate_patch.sh
    
    # 6. Check for Rosetta 2 on Apple Silicon
    if [ "$(uname -m)" = "arm64" ]; then
        _log info "Apple Silicon detected"
        
        if /usr/bin/pgrep -q oahd; then
            _log info "Rosetta 2 is installed"
        else
            _log info "Rosetta 2 not installed (may be needed for some x86 tools)"
        fi
    fi
    
    # 7. Check Python environment
    if [ -d "$repo_root/.venv" ]; then
        _log info "Python venv exists at $repo_root/.venv"
    else
        _log warning "Python venv not found - run install.sh first"
    fi
    
    # 8. Verify miniforge/conda if training is needed
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
    
    _log success "macOS transforms complete"
}

# =============================================================================
# Helper Functions
# =============================================================================

# Install Homebrew packages if missing
ensure_brew_packages() {
    local packages=("$@")
    
    if ! command -v brew &> /dev/null; then
        _log error "Homebrew not installed"
        return 1
    fi
    
    for pkg in "${packages[@]}"; do
        if ! brew list "$pkg" &> /dev/null; then
            _log info "Installing $pkg via Homebrew..."
            brew install "$pkg"
        fi
    done
}

# Get macOS version
get_macos_version() {
    sw_vers -productVersion 2>/dev/null || echo "unknown"
}

# Check if running on Apple Silicon
is_apple_silicon() {
    [ "$(uname -m)" = "arm64" ]
}

# =============================================================================
# Exports
# =============================================================================

export -f transform_env_file
export -f run_os_transforms
export -f ensure_brew_packages
export -f get_macos_version
export -f is_apple_silicon

