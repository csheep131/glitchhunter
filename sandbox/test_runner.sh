#!/bin/bash
# GlitchHunter Sandbox Test Runner
# Executes test suites in isolated Docker environment
#
# Usage: ./test_runner.sh [--timeout SECONDS] [--framework pytest|jest|cargo]

set -euo pipefail

TIMEOUT=60
FRAMEWORK="pytest"
TEST_DIR="/sandbox/repo"
COVERAGE_DIR="/sandbox/coverage"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        --framework)
            FRAMEWORK="$2"
            shift 2
            ;;
        --test-dir)
            TEST_DIR="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo "=== GlitchHunter Sandbox Test Runner ==="
echo "Framework: $FRAMEWORK"
echo "Timeout:   ${TIMEOUT}s"
echo "Test dir:  $TEST_DIR"
echo ""

cd "$TEST_DIR" 2>/dev/null || {
    echo "ERROR: Test directory not found: $TEST_DIR"
    exit 1
}

case "$FRAMEWORK" in
    pytest)
        echo "Running pytest..."
        timeout "${TIMEOUT}s" python -m pytest \
            --tb=short \
            --no-header \
            -q \
            --cov=. \
            --cov-report=json:"${COVERAGE_DIR}/coverage.json" \
            --cov-report=term-missing \
            2>&1
        EXIT_CODE=$?
        ;;

    jest)
        echo "Running jest..."
        timeout "${TIMEOUT}s" npx jest \
            --ci \
            --coverage \
            --coverageDirectory="${COVERAGE_DIR}" \
            2>&1
        EXIT_CODE=$?
        ;;

    cargo)
        echo "Running cargo test..."
        timeout "${TIMEOUT}s" cargo test \
            --workspace \
            2>&1
        EXIT_CODE=$?
        ;;

    *)
        echo "ERROR: Unknown framework: $FRAMEWORK"
        exit 1
        ;;
esac

echo ""
echo "=== Test Exit Code: ${EXIT_CODE} ==="
exit ${EXIT_CODE}
