#!/bin/bash
# =============================================================================
# ChatOS v2.0 - Autonomous Update Pipeline Setup
# =============================================================================
# One-time setup that enables fully autonomous cross-OS updates.
# After running this, the pipeline will automatically run whenever you
# pull/merge/checkout without any manual intervention.
#
# Usage:
#   ./auto-setup.sh              # Enable autonomous updates
#   ./auto-setup.sh --disable    # Disable autonomous updates
#   ./auto-setup.sh --status     # Check current status
#
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[AUTO-SETUP]${NC} $1"; }
log_success() { echo -e "${GREEN}[AUTO-SETUP]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[AUTO-SETUP]${NC} $1"; }

print_banner() {
    echo -e "${CYAN}"
    echo "╔══════════════════════════════════════════════════════════════════╗"
    echo "║      ChatOS v2.0 - Autonomous Update Pipeline Setup              ║"
    echo "║           Set it and forget it - updates run automatically       ║"
    echo "╚══════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

setup_autonomous() {
    print_banner
    
    log_info "Setting up autonomous cross-OS updates..."
    
    # 1. Install git hooks
    log_info "Installing git hooks..."
    bash "$SCRIPT_DIR/install-hooks.sh" --install
    
    # 2. Run initial translation
    log_info "Running initial translation..."
    bash "$SCRIPT_DIR/translate_patch.sh"
    
    # 3. Create marker file
    echo "enabled" > "$REPO_ROOT/.git/chatos-auto-update"
    
    # 4. Configure git to not prompt
    cd "$REPO_ROOT"
    git config core.autocrlf input
    git config core.eol lf
    
    echo ""
    log_success "Autonomous updates enabled!"
    echo ""
    echo -e "${CYAN}What happens now:${NC}"
    echo -e "  • ${GREEN}git pull${NC} → Automatically runs translation"
    echo -e "  • ${GREEN}git merge${NC} → Automatically runs translation"
    echo -e "  • ${GREEN}git checkout${NC} → Automatically runs translation (branch switch)"
    echo ""
    echo -e "${CYAN}The hooks are smart:${NC}"
    echo -e "  • Quick translation runs every time (~2-5 seconds)"
    echo -e "  • Full validation only runs when OS changes"
    echo ""
    echo -e "${YELLOW}To disable:${NC} ./scripts/update/auto-setup.sh --disable"
    echo ""
}

disable_autonomous() {
    print_banner
    
    log_info "Disabling autonomous updates..."
    
    # Remove hooks
    bash "$SCRIPT_DIR/install-hooks.sh" --uninstall
    
    # Remove marker
    rm -f "$REPO_ROOT/.git/chatos-auto-update"
    
    log_success "Autonomous updates disabled"
    echo ""
    echo -e "You can still run updates manually:"
    echo -e "  ${YELLOW}./scripts/update/cross_os_update.sh${NC}"
    echo ""
}

show_status() {
    print_banner
    
    echo -e "${CYAN}Current Status:${NC}"
    echo ""
    
    # Check if enabled
    if [ -f "$REPO_ROOT/.git/chatos-auto-update" ]; then
        echo -e "  Autonomous mode: ${GREEN}ENABLED${NC}"
    else
        echo -e "  Autonomous mode: ${YELLOW}DISABLED${NC}"
    fi
    
    # Check hooks
    bash "$SCRIPT_DIR/install-hooks.sh" --status
    
    # Show last OS
    if [ -f "$REPO_ROOT/.git/chatos-last-os" ]; then
        echo -e "  Last recorded OS: ${CYAN}$(cat "$REPO_ROOT/.git/chatos-last-os")${NC}"
    fi
    
    # Current OS
    local current_os
    case "$(uname -s)" in
        Linux*)  current_os="linux" ;;
        Darwin*) current_os="darwin" ;;
        *)       current_os="unknown" ;;
    esac
    echo -e "  Current OS: ${CYAN}$current_os${NC}"
    echo ""
}

# Main
case "${1:-}" in
    --disable)
        disable_autonomous
        ;;
    --status)
        show_status
        ;;
    *)
        setup_autonomous
        ;;
esac

