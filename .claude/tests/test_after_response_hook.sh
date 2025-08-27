#!/bin/bash
# Test script for after_response.py hook (Stop hook)
# Tests the hook that moves results.md to the correct location when Claude Code finishes

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counters
TESTS_RUN=0
TESTS_PASSED=0

echo -e "${YELLOW}🧪 Testing After Response Hook (Stop hook - results.md mover)${NC}"
echo "========================================================"

# Helper function to run a test
run_test() {
    local test_name="$1"
    local expected_exit_code="$2"
    local expected_output_pattern="$3"
    local test_command="$4"
    
    echo -n "Testing: $test_name ... "
    
    TESTS_RUN=$((TESTS_RUN + 1))
    
    # Run the test and capture output and exit code
    set +e  # Don't exit on error for this test
    output=$(eval "$test_command" 2>&1)
    actual_exit_code=$?
    set -e  # Re-enable exit on error
    
    # Check exit code
    if [ "$actual_exit_code" -ne "$expected_exit_code" ]; then
        echo -e "${RED}FAILED${NC}"
        echo "  Expected exit code: $expected_exit_code"
        echo "  Actual exit code: $actual_exit_code"
        echo "  Output: $output"
        return 1
    fi
    
    # Check output pattern if provided
    if [ -n "$expected_output_pattern" ]; then
        if ! echo "$output" | grep -q "$expected_output_pattern"; then
            echo -e "${RED}FAILED${NC}"
            echo "  Expected output to contain: $expected_output_pattern"
            echo "  Actual output: $output"
            return 1
        fi
    fi
    
    echo -e "${GREEN}PASSED${NC}"
    TESTS_PASSED=$((TESTS_PASSED + 1))
    return 0
}

# Setup test environment
TEST_DIR="/tmp/stackbench_results_test_$$"
ORIGINAL_DIR=$(pwd)
mkdir -p "$TEST_DIR"

echo "Test directory: $TEST_DIR"
echo ""

# Test 1: Hook should skip when CLAUDE_AGENT is not stackbench_overall_analyzer
run_test "Skip for different agent" 0 "Skipping - not overall analyzer" \
    "export CLAUDE_AGENT='some_other_agent' && python .claude/hooks/after_response.py"

# Test 2: Hook should skip when no CLAUDE_OUTPUT_DIR is set
run_test "Skip when no output directory set" 0 "Warning: No CLAUDE_OUTPUT_DIR found" \
    "export CLAUDE_AGENT='stackbench_overall_analyzer' && unset CLAUDE_OUTPUT_DIR && python .claude/hooks/after_response.py"

# Test 3: Hook should report when no results.md found
run_test "Report no results.md found" 0 "No results.md found to move" \
    "export CLAUDE_AGENT='stackbench_overall_analyzer' CLAUDE_OUTPUT_DIR='$TEST_DIR/empty' && python .claude/hooks/after_response.py"

# Test 4: Hook should confirm when file is already in correct location
mkdir -p "$TEST_DIR/correct_location"
echo "# Test Results" > "$TEST_DIR/correct_location/results.md"

run_test "Confirm file in correct location" 0 "already in correct location" \
    "cd '$TEST_DIR/correct_location' && export CLAUDE_AGENT='stackbench_overall_analyzer' CLAUDE_OUTPUT_DIR='$TEST_DIR/correct_location' && python '$ORIGINAL_DIR/.claude/hooks/after_response.py'"

# Test 5: Hook should move file from current working directory to target
mkdir -p "$TEST_DIR/source_dir"
cd "$TEST_DIR/source_dir"
echo "# Test Results CWD" > "results.md"

run_test "Move file from current working directory" 0 "Moved results.md from cwd to" \
    "export CLAUDE_AGENT='stackbench_overall_analyzer' CLAUDE_OUTPUT_DIR='$TEST_DIR/target_dir' && python '$ORIGINAL_DIR/.claude/hooks/after_response.py'"

# Verify the file was actually moved
cd - > /dev/null
if [ -f "$TEST_DIR/target_dir/results.md" ]; then
    echo "  ✓ File successfully moved to target location"
else
    echo "  ✗ File was not found in target location"
    TESTS_PASSED=$((TESTS_PASSED - 1))
fi

# Cleanup
echo ""
echo "Cleaning up test directory: $TEST_DIR"
rm -rf "$TEST_DIR"

# Results summary
echo ""
echo "========================================================"
echo -e "${YELLOW}Test Results Summary${NC}"
echo "Total tests run: $TESTS_RUN"
echo -e "Tests passed: ${GREEN}$TESTS_PASSED${NC}"
echo -e "Tests failed: $((TESTS_RUN - TESTS_PASSED))"

if [ $TESTS_PASSED -eq $TESTS_RUN ]; then
    echo -e "${GREEN}✅ All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}❌ Some tests failed!${NC}"
    exit 1
fi