#!/bin/bash
# Test script for StackBench JSON Validator Hook
# Tests the analyst_json_validator.py hook with various scenarios

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counters
TESTS_RUN=0
TESTS_PASSED=0

echo -e "${YELLOW}🧪 Testing StackBench JSON Validator Hook${NC}"
echo "================================================"

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
TEST_DIR="/tmp/stackbench_test_$$"
mkdir -p "$TEST_DIR"

echo "Test directory: $TEST_DIR"
echo ""

# Test 1: Hook should skip when CLAUDE_AGENT is not stackbench_analyzer
run_test "Skip validation for different agent" 0 "Skipping validation - not StackBench analyzer" \
    "export CLAUDE_AGENT='some_other_agent' && echo '{\"tool_input\": {\"file_path\": \"test.json\"}}' | python .claude/hooks/analyst_json_validator.py"

# Test 2: Hook should skip when CLAUDE_AGENT is empty
run_test "Skip validation when no agent set" 0 "Skipping validation - not StackBench analyzer" \
    "unset CLAUDE_AGENT && echo '{\"tool_input\": {\"file_path\": \"test.json\"}}' | python .claude/hooks/analyst_json_validator.py"

# Test 3: Hook should run for stackbench_analyzer but fail on missing file
run_test "Run validation for stackbench_analyzer (missing file)" 1 "File .* does not exist" \
    "export CLAUDE_AGENT='stackbench_analyzer' CLAUDE_OUTPUT_DIR='$TEST_DIR' && echo '{\"tool_input\": {\"file_path\": \"$TEST_DIR/use_case_99_analysis.json\"}, \"tool_response\": {\"success\": true}}' | python .claude/hooks/analyst_json_validator.py"

# Test 4: Hook should skip non-analysis files
cat > "$TEST_DIR/regular_file.json" << 'EOF'
{"some": "data"}
EOF

run_test "Skip non-analysis JSON files" 0 "Not a StackBench analysis file" \
    "export CLAUDE_AGENT='stackbench_analyzer' && echo '{\"tool_input\": {\"file_path\": \"$TEST_DIR/regular_file.json\"}, \"tool_response\": {\"success\": true}}' | python .claude/hooks/analyst_json_validator.py"

# Test 5: Hook should validate incomplete analysis files and fail
cat > "$TEST_DIR/use_case_1_analysis.json" << 'EOF'
{
  "use_case_number": 1,
  "use_case_name": "Incomplete Test Case"
}
EOF

run_test "Validate incomplete analysis JSON (should fail)" 2 "STACKBENCH JSON VALIDATION FAILED" \
    "export CLAUDE_OUTPUT_DIR='$TEST_DIR' CLAUDE_USE_CASE_ID='use_case_1' CLAUDE_AGENT='stackbench_analyzer' && echo '{\"tool_input\": {\"file_path\": \"$TEST_DIR/use_case_1_analysis.json\"}, \"tool_response\": {\"success\": true}}' | python .claude/hooks/analyst_json_validator.py"

# Test 6: Hook should validate complete analysis files and pass  
cat > "$TEST_DIR/use_case_2_analysis.json" << 'EOF'
{
  "use_case_number": 2,
  "use_case_name": "Complete Test Case",
  "code_executability": {
    "is_executable": true,
    "execution_result": "Test successful",
    "failed_due_to_api_key_error": false
  },
  "underlying_library_usage": {
    "was_used": true,
    "was_mocked": false,
    "mocking_decision_trace": {
      "initial_attempts": [],
      "alternative_approaches": [],
      "final_decision_point": null,
      "mock_strategy": null
    }
  },
  "documentation_tracking": {
    "files_consulted": ["README.md"],
    "implementation_notes": ["Used real API"],
    "evidence_of_usage": "Applied documentation patterns"
  },
  "quality_assessment": {
    "completeness_score": "8 - Most features implemented",
    "clarity_score": "7 - Clear but could be better", 
    "accuracy_score": "9 - Very accurate implementation",
    "example_quality_score": "8 - Good examples provided",
    "overall_score": "8 - Good overall quality",
    "agent_readiness": "ready"
  },
  "improvement_recommendations": []
}
EOF

run_test "Validate complete analysis JSON (should pass)" 0 "STACKBENCH JSON STRUCTURE IS VALID" \
    "export CLAUDE_OUTPUT_DIR='$TEST_DIR' CLAUDE_USE_CASE_ID='use_case_2' CLAUDE_AGENT='stackbench_analyzer' && echo '{\"tool_input\": {\"file_path\": \"$TEST_DIR/use_case_2_analysis.json\"}, \"tool_response\": {\"success\": true}}' | python .claude/hooks/analyst_json_validator.py"

# Test 7: Hook should detect wrong directory
mkdir -p "$TEST_DIR/wrong_dir" 
cat > "$TEST_DIR/wrong_dir/use_case_3_analysis.json" << 'EOF'
{
  "use_case_number": 3,
  "use_case_name": "Wrong Directory Test"
}
EOF

run_test "Detect wrong file location" 1 "WRONG LOCATION: File being saved in wrong directory" \
    "export CLAUDE_OUTPUT_DIR='$TEST_DIR' CLAUDE_USE_CASE_ID='use_case_3' CLAUDE_AGENT='stackbench_analyzer' && echo '{\"tool_input\": {\"file_path\": \"$TEST_DIR/wrong_dir/use_case_3_analysis.json\"}, \"tool_response\": {\"success\": true}}' | python .claude/hooks/analyst_json_validator.py"

# Test 8: Hook should validate partial executable status
cat > "$TEST_DIR/use_case_4_analysis.json" << 'EOF'
{
  "use_case_number": 4,
  "use_case_name": "Partial Execution Test",
  "code_executability": {
    "is_executable": "partial",
    "execution_result": "Partially working",
    "failed_due_to_api_key_error": false
  },
  "underlying_library_usage": {
    "was_used": false,
    "was_mocked": true,
    "mocking_decision_trace": {
      "initial_attempts": [],
      "alternative_approaches": [], 
      "final_decision_point": null,
      "mock_strategy": null
    }
  },
  "documentation_tracking": {
    "files_consulted": [],
    "implementation_notes": [],
    "evidence_of_usage": "Limited usage"
  },
  "quality_assessment": {
    "completeness_score": "5 - Partial implementation",
    "clarity_score": "6 - Somewhat clear",
    "accuracy_score": "7 - Mostly accurate",
    "example_quality_score": "5 - Limited examples",
    "overall_score": "6 - Needs improvement",
    "agent_readiness": "needs_improvement"
  },
  "improvement_recommendations": [
    {
      "priority": "high",
      "category": "missing_info",
      "issue": "Incomplete implementation",
      "recommendation": "Add missing features",
      "expected_impact": "Would improve completeness"
    }
  ]
}
EOF

run_test "Validate partial executable status" 0 "Executable=PARTIAL" \
    "export CLAUDE_OUTPUT_DIR='$TEST_DIR' CLAUDE_USE_CASE_ID='use_case_4' CLAUDE_AGENT='stackbench_analyzer' && echo '{\"tool_input\": {\"file_path\": \"$TEST_DIR/use_case_4_analysis.json\"}, \"tool_response\": {\"success\": true}}' | python .claude/hooks/analyst_json_validator.py"

# Cleanup
echo ""
echo "Cleaning up test directory: $TEST_DIR"
rm -rf "$TEST_DIR"

# Results summary
echo ""
echo "================================================"
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