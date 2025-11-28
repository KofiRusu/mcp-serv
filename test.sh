#!/bin/bash
# ChatOS Test Runner
# Usage: ./test.sh [options]
#
# Options:
#   -a, --all       Run all tests including E2E (requires Playwright)
#   -u, --unit      Run unit tests only
#   -i, --int       Run integration tests only
#   -e, --e2e       Run E2E tests only (requires Playwright and running server)
#   -c, --cov       Generate coverage report
#   -v, --verbose   Verbose output

set -e

cd "$(dirname "$0")"

# Activate virtual environment
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Default options
TESTS=""
VERBOSE=""
COVERAGE=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -a|--all)
            TESTS="tests/"
            shift
            ;;
        -u|--unit)
            TESTS="tests/test_memory_logger.py tests/test_auto_trainer.py tests/test_model_config.py tests/test_accessibility.py"
            shift
            ;;
        -i|--int)
            TESTS="tests/test_ollama.py tests/test_providers.py tests/test_api.py"
            shift
            ;;
        -e|--e2e)
            TESTS="tests/test_e2e.py"
            shift
            ;;
        -c|--cov)
            COVERAGE="--cov=ChatOS --cov-report=html --cov-report=term-missing"
            shift
            ;;
        -v|--verbose)
            VERBOSE="-v"
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Default to unit tests if no tests specified
if [ -z "$TESTS" ]; then
    TESTS="tests/test_memory_logger.py tests/test_auto_trainer.py tests/test_model_config.py tests/test_providers.py tests/test_accessibility.py"
fi

echo "=========================================="
echo "ChatOS Test Suite"
echo "=========================================="
echo ""

# Run tests
python -m pytest $TESTS $VERBOSE $COVERAGE --tb=short

echo ""
echo "=========================================="
echo "Tests completed!"
echo "=========================================="

