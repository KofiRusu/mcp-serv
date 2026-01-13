#!/bin/bash
# =============================================================================
# ChatOS v2.0 - Translation Patch Script
# =============================================================================
# Applies OS-specific transformations to ensure cross-platform compatibility.
#
# Transformations applied:
#   1. Normalize line endings (CRLF -> LF)
#   2. Set executable bits on shell scripts
#   3. Generate .env.local from .env.example with OS-specific values
#   4. Apply OS-specific configuration adjustments
#
# Usage:
#   ./translate_patch.sh [--verbose]
#
# =============================================================================

set -e

# =============================================================================
# Configuration
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

VERBOSE=false

# =============================================================================
# Functions
# =============================================================================

log_info() {
    echo -e "${BLUE}[TRANSLATE]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[TRANSLATE]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[TRANSLATE]${NC} $1"
}

log_error() {
    echo -e "${RED}[TRANSLATE]${NC} $1"
}

log_verbose() {
    if [ "$VERBOSE" = true ]; then
        echo -e "${CYAN}[TRANSLATE]${NC} $1"
    fi
}

detect_os() {
    local os_name
    os_name="$(uname -s)"
    
    case "$os_name" in
        Linux*)     echo "linux" ;;
        Darwin*)    echo "darwin" ;;
        *)          echo "unknown" ;;
    esac
}

detect_arch() {
    local arch
    arch="$(uname -m)"
    
    case "$arch" in
        x86_64)         echo "x86_64" ;;
        arm64|aarch64)  echo "arm64" ;;
        *)              echo "unknown" ;;
    esac
}

# =============================================================================
# Transform: Line Endings
# =============================================================================

normalize_line_endings() {
    log_info "Normalizing line endings (CRLF -> LF)..."
    
    local count=0
    local file_patterns=("*.sh" "*.py" "*.ts" "*.tsx" "*.js" "*.json" "*.md" "*.yaml" "*.yml")
    
    for pattern in "${file_patterns[@]}"; do
        while IFS= read -r -d '' file; do
            # Check if file contains CRLF
            if grep -q $'\r' "$file" 2>/dev/null; then
                if [ "$VERBOSE" = true ]; then
                    log_verbose "Converting: $file"
                fi
                # Convert CRLF to LF
                if command -v sed &> /dev/null; then
                    sed -i.bak 's/\r$//' "$file" && rm -f "${file}.bak"
                    count=$((count + 1))
                fi
            fi
        done < <(find "$REPO_ROOT" -type f -name "$pattern" \
            -not -path "*/node_modules/*" \
            -not -path "*/.venv/*" \
            -not -path "*/__pycache__/*" \
            -not -path "*/.git/*" \
            -not -path "*/.next/*" \
            -not -path "*/dist/*" \
            -not -path "*/build/*" \
            -not -path "*/.cache/*" \
            -print0 2>/dev/null || true)
    done
    
    if [ $count -gt 0 ]; then
        log_success "Converted $count files from CRLF to LF"
    else
        log_info "No CRLF line endings found"
    fi
}

# =============================================================================
# Transform: Executable Bits
# =============================================================================

set_executable_bits() {
    log_info "Setting executable bits on scripts..."
    
    local count=0
    
    # Shell scripts
    while IFS= read -r -d '' file; do
        if [ ! -x "$file" ]; then
            chmod +x "$file"
            log_verbose "chmod +x: $file"
            count=$((count + 1))
        fi
    done < <(find "$REPO_ROOT" -type f -name "*.sh" \
        -not -path "*/node_modules/*" \
        -not -path "*/.venv/*" \
        -print0 2>/dev/null || true)
    
    # CLI tools
    local cli_files=("$REPO_ROOT/cli/chatos" "$REPO_ROOT/cli/trading" "$REPO_ROOT/cli/hf-trading")
    for file in "${cli_files[@]}"; do
        if [ -f "$file" ] && [ ! -x "$file" ]; then
            chmod +x "$file"
            log_verbose "chmod +x: $file"
            count=$((count + 1))
        fi
    done
    
    if [ $count -gt 0 ]; then
        log_success "Set executable bit on $count files"
    else
        log_info "All scripts already executable"
    fi
}

# =============================================================================
# Transform: Environment Files
# =============================================================================

generate_env_local() {
    log_info "Generating .env.local files..."
    
    local current_os
    current_os=$(detect_os)
    
    # Root .env.local
    local env_example="$REPO_ROOT/.env.example"
    local env_local="$REPO_ROOT/.env.local"
    
    if [ -f "$env_example" ]; then
        if [ ! -f "$env_local" ]; then
            log_info "Creating $env_local from template..."
            cp "$env_example" "$env_local"
            
            # Apply OS-specific transforms
            if [ -f "$SCRIPT_DIR/transforms/${current_os}.sh" ]; then
                source "$SCRIPT_DIR/transforms/${current_os}.sh"
                if declare -f transform_env_file &> /dev/null; then
                    transform_env_file "$env_local"
                fi
            fi
            
            log_success "Created $env_local"
        else
            log_info ".env.local already exists (skipping)"
        fi
    else
        log_warning ".env.example not found (skipping .env.local generation)"
    fi
    
    # Frontend .env.local
    local frontend_env_example="$REPO_ROOT/frontend/.env.example"
    local frontend_env_local="$REPO_ROOT/frontend/.env.local"
    
    if [ -f "$frontend_env_example" ]; then
        if [ ! -f "$frontend_env_local" ]; then
            log_info "Creating frontend .env.local from template..."
            cp "$frontend_env_example" "$frontend_env_local"
            log_success "Created frontend/.env.local"
        else
            log_info "frontend/.env.local already exists (skipping)"
        fi
    fi
}

# =============================================================================
# Transform: OS-Specific Configurations
# =============================================================================

apply_os_transforms() {
    log_info "Applying OS-specific transforms..."
    
    local current_os
    current_os=$(detect_os)
    
    # Source common transforms
    if [ -f "$SCRIPT_DIR/transforms/common.sh" ]; then
        source "$SCRIPT_DIR/transforms/common.sh"
    fi
    
    # Source OS-specific transforms
    local os_transform="$SCRIPT_DIR/transforms/${current_os}.sh"
    if [ -f "$os_transform" ]; then
        log_info "Loading transforms for: $current_os"
        source "$os_transform"
        
        # Run OS-specific transform function if it exists
        if declare -f run_os_transforms &> /dev/null; then
            run_os_transforms "$REPO_ROOT"
        fi
        
        log_success "Applied $current_os transforms"
    else
        log_warning "No transforms found for: $current_os"
    fi
}

# =============================================================================
# Transform: Git Config
# =============================================================================

configure_git_settings() {
    log_info "Configuring git settings..."
    
    cd "$REPO_ROOT"
    
    # Ensure consistent line ending handling
    git config core.autocrlf input 2>/dev/null || true
    git config core.eol lf 2>/dev/null || true
    
    # Store current OS
    local current_os
    current_os=$(detect_os)
    echo "$current_os" > "$REPO_ROOT/.git/chatos-current-os" 2>/dev/null || true
    
    log_success "Git configured for cross-OS compatibility"
}

# =============================================================================
# Main
# =============================================================================

main() {
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --verbose|-v)
                VERBOSE=true
                shift
                ;;
            *)
                shift
                ;;
        esac
    done
    
    local current_os
    current_os=$(detect_os)
    
    log_info "Starting translation phase for: $current_os"
    log_info "Repository: $REPO_ROOT"
    
    # Run transforms
    normalize_line_endings
    set_executable_bits
    generate_env_local
    apply_os_transforms
    configure_git_settings
    
    log_success "Translation phase complete!"
}

# Run main
main "$@"

