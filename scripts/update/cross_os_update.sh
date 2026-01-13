#!/bin/bash
# =============================================================================
# ChatOS v2.0 - Cross-OS Update Pipeline
# =============================================================================
# Main entry point for the bidirectional Linux <-> macOS update pipeline.
# 
# Features:
#   - Auto-detects current OS
#   - Runs OS-specific transformations
#   - Validates the codebase works on target OS
#   - Idempotent: safe to run multiple times
#
# Usage:
#   ./cross_os_update.sh                      # Auto-detect, run all
#   ./cross_os_update.sh --translate-only     # Skip validation
#   ./cross_os_update.sh --verify-only        # Skip translation
#   ./cross_os_update.sh --dry-run            # Show what would happen
#   ./cross_os_update.sh --help               # Show help
#
# =============================================================================

set -e

# =============================================================================
# Configuration
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Default options
RUN_TRANSLATE=true
RUN_VERIFY=true
DRY_RUN=false
VERBOSE=false

# =============================================================================
# Functions
# =============================================================================

print_banner() {
    echo -e "${CYAN}"
    echo "╔══════════════════════════════════════════════════════════════════╗"
    echo "║         ChatOS v2.0 - Cross-OS Update Pipeline                   ║"
    echo "║              Linux <-> macOS Bidirectional Sync                  ║"
    echo "╚══════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "\n${CYAN}▶ $1${NC}"
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

show_help() {
    cat << EOF
ChatOS v2.0 - Cross-OS Update Pipeline

USAGE:
    ./cross_os_update.sh [OPTIONS]

OPTIONS:
    --translate-only    Run translation phase only (skip validation)
    --verify-only       Run verification phase only (skip translation)
    --dry-run           Show what would happen without making changes
    --verbose, -v       Enable verbose output
    --help, -h          Show this help message

DESCRIPTION:
    This script ensures ChatOS code works correctly when moving between
    Linux and macOS. It handles:
    
    1. TRANSLATION PHASE
       - Normalizes line endings (CRLF -> LF)
       - Sets executable bits on shell scripts
       - Generates .env.local from .env.example with OS-specific values
       - Applies OS-specific configuration adjustments
    
    2. VERIFICATION PHASE
       - Python syntax check
       - Unit tests (pytest)
       - Frontend build (npm)
       - Backend startup + health check

EXAMPLES:
    # Full update (translate + verify)
    ./cross_os_update.sh
    
    # Only run translation (quick)
    ./cross_os_update.sh --translate-only
    
    # Only run verification (after manual changes)
    ./cross_os_update.sh --verify-only
    
    # See what would happen
    ./cross_os_update.sh --dry-run

EXIT CODES:
    0   Success
    1   Translation failed
    2   Verification failed
    3   Unknown error

EOF
}

parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --translate-only)
                RUN_VERIFY=false
                shift
                ;;
            --verify-only)
                RUN_TRANSLATE=false
                shift
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --verbose|-v)
                VERBOSE=true
                shift
                ;;
            --help|-h)
                show_help
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                echo "Use --help for usage information"
                exit 1
                ;;
        esac
    done
}

check_prerequisites() {
    log_step "Checking prerequisites..."
    
    local missing=false
    
    # Check bash version
    if [[ "${BASH_VERSINFO[0]}" -lt 4 ]]; then
        log_warning "Bash 4+ recommended (found: ${BASH_VERSION})"
    else
        log_info "Bash ${BASH_VERSION}"
    fi
    
    # Check required tools
    local tools=("git" "python3" "node" "npm")
    for tool in "${tools[@]}"; do
        if command -v "$tool" &> /dev/null; then
            if [ "$VERBOSE" = true ]; then
                log_info "$tool: $(command -v "$tool")"
            fi
        else
            log_error "$tool not found"
            missing=true
        fi
    done
    
    if [ "$missing" = true ]; then
        log_error "Missing prerequisites. Please install missing tools."
        exit 1
    fi
    
    log_success "All prerequisites satisfied"
}

run_translation() {
    log_step "Running translation phase..."
    
    if [ "$DRY_RUN" = true ]; then
        log_info "[DRY RUN] Would run: $SCRIPT_DIR/translate_patch.sh"
        return 0
    fi
    
    if [ ! -f "$SCRIPT_DIR/translate_patch.sh" ]; then
        log_error "translate_patch.sh not found at $SCRIPT_DIR"
        exit 1
    fi
    
    # Run translation script
    if [ "$VERBOSE" = true ]; then
        bash "$SCRIPT_DIR/translate_patch.sh" --verbose
    else
        bash "$SCRIPT_DIR/translate_patch.sh"
    fi
    
    local exit_code=$?
    if [ $exit_code -ne 0 ]; then
        log_error "Translation phase failed (exit code: $exit_code)"
        exit 1
    fi
    
    log_success "Translation phase completed"
}

run_verification() {
    log_step "Running verification phase..."
    
    if [ "$DRY_RUN" = true ]; then
        log_info "[DRY RUN] Would run: $SCRIPT_DIR/verify_target.sh"
        return 0
    fi
    
    if [ ! -f "$SCRIPT_DIR/verify_target.sh" ]; then
        log_error "verify_target.sh not found at $SCRIPT_DIR"
        exit 1
    fi
    
    # Run verification script
    if [ "$VERBOSE" = true ]; then
        bash "$SCRIPT_DIR/verify_target.sh" --verbose
    else
        bash "$SCRIPT_DIR/verify_target.sh"
    fi
    
    local exit_code=$?
    if [ $exit_code -ne 0 ]; then
        log_error "Verification phase failed (exit code: $exit_code)"
        exit 2
    fi
    
    log_success "Verification phase completed"
}

print_summary() {
    local current_os
    local current_arch
    current_os=$(detect_os)
    current_arch=$(detect_arch)
    
    echo ""
    echo -e "${GREEN}════════════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}✅ Cross-OS Update Pipeline Completed Successfully!${NC}"
    echo -e "${GREEN}════════════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "${CYAN}System Information:${NC}"
    echo -e "  OS:           $current_os"
    echo -e "  Architecture: $current_arch"
    echo -e "  Repo Root:    $REPO_ROOT"
    echo ""
    echo -e "${CYAN}What was done:${NC}"
    if [ "$RUN_TRANSLATE" = true ]; then
        echo -e "  ${GREEN}✓${NC} Translation phase (OS-specific transforms applied)"
    fi
    if [ "$RUN_VERIFY" = true ]; then
        echo -e "  ${GREEN}✓${NC} Verification phase (all checks passed)"
    fi
    echo ""
    echo -e "${CYAN}Next steps:${NC}"
    echo -e "  1. Review any generated .env.local files"
    echo -e "  2. Start the server: ${YELLOW}./run.sh${NC}"
    echo -e "  3. Access UI: ${YELLOW}http://localhost:3000${NC}"
    echo ""
}

# =============================================================================
# Main
# =============================================================================

main() {
    parse_args "$@"
    
    print_banner
    
    # Detect and display current OS
    local current_os
    local current_arch
    current_os=$(detect_os)
    current_arch=$(detect_arch)
    
    log_info "Detected OS: $current_os ($current_arch)"
    log_info "Repository: $REPO_ROOT"
    
    if [ "$current_os" = "unknown" ]; then
        log_error "Unknown OS. This script supports Linux and macOS only."
        exit 1
    fi
    
    # Store current OS for hooks/future reference
    echo "$current_os" > "$REPO_ROOT/.git/chatos-current-os" 2>/dev/null || true
    
    # Change to repo root
    cd "$REPO_ROOT"
    
    # Check prerequisites
    check_prerequisites
    
    # Run phases
    if [ "$RUN_TRANSLATE" = true ]; then
        run_translation
    fi
    
    if [ "$RUN_VERIFY" = true ]; then
        run_verification
    fi
    
    # Print summary
    if [ "$DRY_RUN" = false ]; then
        print_summary
    else
        echo ""
        log_info "[DRY RUN] No changes were made"
    fi
}

# Run main
main "$@"

