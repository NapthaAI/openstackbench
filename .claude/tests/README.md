# StackBench Claude Code Hook Tests

This directory contains test scripts for StackBench's Claude Code hooks.

## Test Files

### `test_analyst_json_validator.sh`

Comprehensive test suite for the `analyst_json_validator.py` hook.

**Usage:**
```bash
.claude/tests/test_analyst_json_validator.sh
```

**What it tests:**
- ✅ Hook only runs when `CLAUDE_AGENT=stackbench_analyzer`
- ✅ Hook skips validation for other agents
- ✅ Hook properly validates StackBench analysis JSON structure
- ✅ Hook detects missing required fields
- ✅ Hook validates file location against environment variables
- ✅ Hook handles partial executable status correctly
- ✅ Hook skips non-analysis files

**Test scenarios:**
1. Skip validation for different agent
2. Skip validation when no agent set
3. Run validation for stackbench_analyzer (missing file)
4. Skip non-analysis JSON files
5. Validate incomplete analysis JSON (should fail)
6. Validate complete analysis JSON (should pass)
7. Detect wrong file location
8. Validate partial executable status

## Running Tests

All tests are designed to be self-contained and clean up after themselves. They use temporary directories and don't affect the main StackBench installation.

The test script will report:
- Total tests run
- Number of passed/failed tests
- Detailed failure information if any test fails
- Exit code 0 on success, 1 on failure (suitable for CI/CD)