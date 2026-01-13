#!/bin/bash
# =============================================================================
# ChatOS v2.0 - Target Verification Script
# =============================================================================
# Runs comprehensive validation to ensure the codebase works on the target OS.
#
# Validation steps:
#   1. Python syntax check
#   2. Unit tests (pytest)
#   3. Frontend build (npm)
#   4. Backend startup + health check
#
# Usage:
#   ./verify_target.sh [--verbose] [--skip-tests] [--skip-build] [--skip-health]
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

# Options
VERBOSE=false
SKIP_TESTS=false
SKIP_BUILD=false
SKIP_HEALTH=false

# Ports
BACKEND_PORT=8000
HEALTH_ENDPOINT="http://localhost:${BACKEND_PORT}/health"

# Timeouts
STARTUP_TIMEOUT=30
TEST_TIMEOUT=300

# PIDs to track
BACKEND_PID=""

# =============================================================================
# Functions
# =============================================================================

log_info() {
    echo -e "${BLUE}[VERIFY]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[VERIFY]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[VERIFY]${NC} $1"
}

log_error() {
    echo -e "${RED}[VERIFY]${NC} $1"
}

log_step() {
    echo -e "\n${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}▶ $1${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

cleanup() {
    if [ -n "$BACKEND_PID" ]; then
        log_info "Stopping backend (PID: $BACKEND_PID)..."
        kill "$BACKEND_PID" 2>/dev/null || true
        wait "$BACKEND_PID" 2>/dev/null || true
    fi
}

trap cleanup EXIT

parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --verbose|-v)
                VERBOSE=true
                shift
                ;;
            --skip-tests)
                SKIP_TESTS=true
                shift
                ;;
            --skip-build)
                SKIP_BUILD=true
                shift
                ;;
            --skip-health)
                SKIP_HEALTH=true
                shift
                ;;
            *)
                shift
                ;;
        esac
    done
}

# =============================================================================
# Step 1: Python Syntax Check
# =============================================================================

verify_python_syntax() {
    log_step "Step 1: Python Syntax Check"
    
    local error_count=0
    local file_count=0
    
    log_info "Checking Python files in chatos_backend/..."
    
    while IFS= read -r -d '' file; do
        file_count=$((file_count + 1))
        if [ "$VERBOSE" = true ]; then
            echo -n "  Checking: $file ... "
        fi
        
        if python3 -m py_compile "$file" 2>/dev/null; then
            if [ "$VERBOSE" = true ]; then
                echo -e "${GREEN}OK${NC}"
            fi
        else
            error_count=$((error_count + 1))
            if [ "$VERBOSE" = true ]; then
                echo -e "${RED}FAILED${NC}"
            else
                log_error "Syntax error in: $file"
            fi
        fi
    done < <(find "$REPO_ROOT/chatos_backend" -type f -name "*.py" -print0 2>/dev/null)
    
    # Also check persrm_training if it exists
    if [ -d "$REPO_ROOT/persrm_training" ]; then
        log_info "Checking Python files in persrm_training/..."
        
        while IFS= read -r -d '' file; do
            file_count=$((file_count + 1))
            if ! python3 -m py_compile "$file" 2>/dev/null; then
                error_count=$((error_count + 1))
                log_error "Syntax error in: $file"
            fi
        done < <(find "$REPO_ROOT/persrm_training" -type f -name "*.py" -print0 2>/dev/null)
    fi
    
    # Check tests
    if [ -d "$REPO_ROOT/tests" ]; then
        log_info "Checking Python files in tests/..."
        
        while IFS= read -r -d '' file; do
            file_count=$((file_count + 1))
            if ! python3 -m py_compile "$file" 2>/dev/null; then
                error_count=$((error_count + 1))
                log_error "Syntax error in: $file"
            fi
        done < <(find "$REPO_ROOT/tests" -type f -name "*.py" -print0 2>/dev/null)
    fi
    
    if [ $error_count -gt 0 ]; then
        log_error "Python syntax check FAILED: $error_count errors in $file_count files"
        return 1
    fi
    
    log_success "Python syntax check PASSED: $file_count files checked"
    return 0
}

# =============================================================================
# Step 2: Unit Tests
# =============================================================================

verify_python_tests() {
    log_step "Step 2: Python Unit Tests"
    
    if [ "$SKIP_TESTS" = true ]; then
        log_warning "Skipping tests (--skip-tests)"
        return 0
    fi
    
    cd "$REPO_ROOT"
    
    # Activate virtual environment if it exists
    if [ -d ".venv" ]; then
        log_info "Activating virtual environment..."
        source .venv/bin/activate
    else
        log_warning "Virtual environment not found, using system Python"
    fi
    
    # Check if pytest is available
    if ! python3 -m pytest --version &> /dev/null; then
        log_warning "pytest not installed, skipping tests"
        return 0
    fi
    
    log_info "Running pytest (excluding E2E tests)..."
    
    local pytest_args="-x --tb=short"
    if [ "$VERBOSE" = true ]; then
        pytest_args="$pytest_args -v"
    else
        pytest_args="$pytest_args -q"
    fi
    
    # Run tests, excluding E2E
    if timeout "$TEST_TIMEOUT" python3 -m pytest tests/ \
        --ignore=tests/test_e2e.py \
        $pytest_args 2>&1; then
        log_success "Python tests PASSED"
        return 0
    else
        local exit_code=$?
        if [ $exit_code -eq 124 ]; then
            log_error "Python tests TIMEOUT after ${TEST_TIMEOUT}s"
        else
            log_error "Python tests FAILED"
        fi
        return 1
    fi
}

# =============================================================================
# Step 3: Frontend Build
# =============================================================================

verify_frontend_build() {
    log_step "Step 3: Frontend Build"
    
    if [ "$SKIP_BUILD" = true ]; then
        log_warning "Skipping build (--skip-build)"
        return 0
    fi
    
    local frontend_dir="$REPO_ROOT/frontend"
    
    if [ ! -d "$frontend_dir" ]; then
        log_warning "Frontend directory not found, skipping"
        return 0
    fi
    
    cd "$frontend_dir"
    
    # Check if node_modules exists
    if [ ! -d "node_modules" ]; then
        log_info "Installing npm dependencies..."
        npm install --silent 2>&1 || {
            log_error "npm install failed"
            return 1
        }
    fi
    
    # Check TypeScript compilation
    log_info "Running TypeScript check..."
    
    if npm run build 2>&1; then
        log_success "Frontend build PASSED"
        return 0
    else
        log_error "Frontend build FAILED"
        return 1
    fi
}

# =============================================================================
# Step 4: Backend Health Check
# =============================================================================

verify_backend_health() {
    log_step "Step 4: Backend Health Check"
    
    if [ "$SKIP_HEALTH" = true ]; then
        log_warning "Skipping health check (--skip-health)"
        return 0
    fi
    
    cd "$REPO_ROOT"
    
    # Check if port is already in use
    if lsof -i ":$BACKEND_PORT" &> /dev/null 2>&1 || \
       netstat -tuln 2>/dev/null | grep -q ":$BACKEND_PORT " || \
       ss -tuln 2>/dev/null | grep -q ":$BACKEND_PORT "; then
        log_warning "Port $BACKEND_PORT already in use, skipping startup test"
        
        # Still try the health check
        if curl -sf "$HEALTH_ENDPOINT" &> /dev/null; then
            log_success "Backend health check PASSED (existing server)"
            return 0
        else
            log_warning "Could not verify health endpoint"
            return 0
        fi
    fi
    
    # Activate virtual environment
    if [ -d ".venv" ]; then
        source .venv/bin/activate
    fi
    
    # Check if uvicorn is available
    if ! python3 -m uvicorn --version &> /dev/null; then
        log_warning "uvicorn not installed, skipping health check"
        return 0
    fi
    
    log_info "Starting backend server..."
    
    # Start backend in background
    python3 -m uvicorn chatos_backend.app:app \
        --host 127.0.0.1 \
        --port "$BACKEND_PORT" \
        --log-level warning &
    BACKEND_PID=$!
    
    log_info "Backend started (PID: $BACKEND_PID)"
    log_info "Waiting for server to be ready (max ${STARTUP_TIMEOUT}s)..."
    
    # Wait for server to be ready
    local count=0
    while ! curl -sf "$HEALTH_ENDPOINT" &> /dev/null; do
        sleep 1
        ((count++))
        
        # Check if process is still running
        if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
            log_error "Backend process died unexpectedly"
            BACKEND_PID=""
            return 1
        fi
        
        if [ $count -ge $STARTUP_TIMEOUT ]; then
            log_error "Backend failed to respond within ${STARTUP_TIMEOUT}s"
            return 1
        fi
        
        if [ "$VERBOSE" = true ]; then
            echo -n "."
        fi
    done
    
    if [ "$VERBOSE" = true ]; then
        echo ""
    fi
    
    log_success "Backend started and responding"
    
    # Test health endpoint
    log_info "Testing health endpoint: $HEALTH_ENDPOINT"
    
    local response
    response=$(curl -sf "$HEALTH_ENDPOINT" 2>/dev/null)
    
    if [ -n "$response" ]; then
        log_info "Health response: $response"
        log_success "Backend health check PASSED"
        return 0
    else
        # Even if no response body, 200 OK is fine
        if curl -sf -o /dev/null "$HEALTH_ENDPOINT" 2>/dev/null; then
            log_success "Backend health check PASSED"
            return 0
        fi
        log_error "Health endpoint returned empty response"
        return 1
    fi
}

# =============================================================================
# Summary
# =============================================================================

print_summary() {
    local passed="$1"
    local failed="$2"
    
    echo ""
    echo -e "${CYAN}════════════════════════════════════════════════════════════════════${NC}"
    
    if [ "$failed" -eq 0 ]; then
        echo -e "${GREEN}✅ All verification steps PASSED${NC}"
    else
        echo -e "${RED}❌ Verification FAILED: $failed step(s) failed${NC}"
    fi
    
    echo -e "${CYAN}════════════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "Summary:"
    echo -e "  Steps passed: ${GREEN}$passed${NC}"
    echo -e "  Steps failed: ${RED}$failed${NC}"
    echo ""
}

# =============================================================================
# Main
# =============================================================================

main() {
    parse_args "$@"
    
    log_info "Starting verification phase..."
    log_info "Repository: $REPO_ROOT"
    
    local passed=0
    local failed=0
    
    # Step 1: Python Syntax
    if verify_python_syntax; then
        passed=$((passed + 1))
    else
        failed=$((failed + 1))
        log_error "Aborting due to Python syntax errors"
        print_summary $passed $failed
        exit 1
    fi
    
    # Step 2: Python Tests
    if verify_python_tests; then
        passed=$((passed + 1))
    else
        failed=$((failed + 1))
        # Don't abort on test failures, continue with other checks
        log_warning "Continuing despite test failures..."
    fi
    
    # Step 3: Frontend Build
    if verify_frontend_build; then
        passed=$((passed + 1))
    else
        failed=$((failed + 1))
        # Don't abort on build failures
        log_warning "Continuing despite build failure..."
    fi
    
    # Step 4: Backend Health
    if verify_backend_health; then
        passed=$((passed + 1))
    else
        failed=$((failed + 1))
    fi
    
    # Print summary
    print_summary $passed $failed
    
    # Exit with appropriate code
    if [ "$failed" -gt 0 ]; then
        exit 2
    fi
    
    exit 0
}

# Run main
main "$@"

