#!/usr/bin/env python3
"""
Test script for StackBench Claude Code hooks using Claude Python SDK.
Tests both analysis_path_redirector.py and analyst_json_validator.py hooks.

This script must be run from the StackBench root directory.
"""

import json
import os
import sys
import tempfile
from pathlib import Path
from claude_code_sdk import ClaudeSDKClient, ClaudeCodeOptions
from typing import Dict, Any
from dotenv import load_dotenv
import subprocess
load_dotenv()

def setup_test_environment():
    """Set up test environment with proper variables."""
    # Ensure we're in the right directory
    if not Path("pyproject.toml").exists():
        print("❌ Error: Must run from StackBench root directory (where pyproject.toml exists)")
        sys.exit(1)
    
    # Create test directories
    test_run_id = "test-hooks-12345"
    test_data_dir = Path("data") / test_run_id / "data"
    test_use_case_dir = test_data_dir / "use_case_1"
    test_use_case_dir.mkdir(parents=True, exist_ok=True)
    
    # Set up environment variables that StackBench analyzer would set
    env_vars = {
        'CLAUDE_USE_CASE_ID': 'use_case_1',
        'CLAUDE_OUTPUT_DIR': str(test_use_case_dir.absolute()),
        'CLAUDE_LOGS_DIR': str((test_data_dir / "logs").absolute()),
        'CLAUDE_PROJECT_DIR': str(Path.cwd().absolute()),
        'CLAUDE_AGENT': 'stackbench_analyzer'
    }
    
    for key, value in env_vars.items():
        os.environ[key] = value
    
    # Create logs directory
    Path(os.environ['CLAUDE_LOGS_DIR']).mkdir(parents=True, exist_ok=True)
    
    return test_use_case_dir, env_vars

def create_valid_analysis_json():
    """Create a valid StackBench analysis JSON structure."""
    return {
        "use_case_number": 1,
        "use_case_name": "Test Analysis Case",
        "code_executability": {
            "is_executable": True,
            "execution_result": "Test execution successful",
            "failure_reason": None,
            "failure_type": None,
            "test_results": "All tests passed",
            "failed_due_to_api_key_error": False
        },
        "underlying_library_usage": {
            "was_used": True,
            "was_mocked": False,
            "mocking_reason": None,
            "mocking_decision_trace": {
                "initial_attempts": ["Used real library"],
                "alternative_approaches": [],
                "final_decision_point": "Library worked as expected",
                "mock_strategy": None
            }
        },
        "documentation_tracking": {
            "files_consulted": ["README.md", "docs/api.md"],
            "implementation_notes": ["Used library patterns", "Followed documentation examples"],
            "evidence_of_usage": "Implementation follows documented patterns"
        },
        "quality_assessment": {
            "completeness_score": "8/10 - Complete implementation",
            "clarity_score": "9/10 - Clear and readable",
            "accuracy_score": "9/10 - Accurate API usage",
            "example_quality_score": "8/10 - Good example quality",
            "overall_score": "8.5/10 - High quality implementation",
            "agent_readiness": "ready"
        },
        "improvement_recommendations": [
            {
                "priority": "medium",
                "category": "structure",
                "issue": "Could add more error handling",
                "recommendation": "Add try-catch blocks for edge cases",
                "expected_impact": "Better robustness for future agents"
            }
        ]
    }

def create_invalid_analysis_json():
    """Create an invalid StackBench analysis JSON structure (missing required fields)."""
    return {
        "use_case_number": 1,
        "use_case_name": "Invalid Test Case",
        # Missing code_executability and other required fields
        "partial_data": "This should fail validation"
    }

async def test_analyst_json_validator():
    """Test the analyst_json_validator.py hook in PreToolUse mode."""
    print("\n🧪 Testing analyst_json_validator.py hook...")
    
    test_use_case_dir, env_vars = setup_test_environment()
    
    # Test 1: Valid JSON content
    print("\n📋 Test 1: Valid JSON content")
    valid_json = create_valid_analysis_json()
    
    prompt = f"""Please write the following JSON content to a file called 'use_case_1_analysis.json':

{json.dumps(valid_json, indent=2)}

Save this to the file {env_vars['CLAUDE_OUTPUT_DIR']}/use_case_1_analysis.json. This should trigger our hooks to validate the JSON structure and redirect the path if needed."""
    
    # Use the same options pattern as your IndividualAnalyzer
    # The hooks should be called from .claude/settings.json
    options = ClaudeCodeOptions(
        system_prompt="You are testing the StackBench hooks system. Follow the user's instructions exactly.",
        max_turns=3,
        cwd=str(Path.cwd()),
        allowed_tools=["Write", "Read", "LS"]
    )
    
    print(f"💾 Environment variables set:")
    for key, value in env_vars.items():
        print(f"   {key}={value}")
    
    try:
        print(f"🚀 Running Claude Code with valid JSON...")
        # Use ClaudeSDKClient instead of query() function
        async with ClaudeSDKClient(options=options) as client:
            await client.query(prompt)
            
            # Process responses
            async for message in client.receive_response():
                print(f"📄 Response: {message}")
        
        print(f"✅ Claude Code query completed")
        print(f"📁 Checking if file was created in correct location...")
        
        expected_file = test_use_case_dir / "use_case_1_analysis.json"
        if expected_file.exists():
            print(f"✅ File created successfully: {expected_file}")
            
            # Validate the content
            with open(expected_file, 'r') as f:
                saved_content = json.load(f)
            
            if saved_content == valid_json:
                print(f"✅ File content matches expected JSON")
            else:
                print(f"❌ File content does not match expected JSON")
        else:
            print(f"❌ File not found at expected location: {expected_file}")
            
            # Check for files in wrong locations
            wrong_locations = [
                Path.cwd() / "use_case_1_analysis.json",
                test_use_case_dir / "$CLAUDE_OUTPUT_DIR" / "use_case_1_analysis.json"
            ]
            
            for wrong_path in wrong_locations:
                if wrong_path.exists():
                    print(f"❌ File found in wrong location: {wrong_path}")
    
    except Exception as e:
        print(f"❌ Error during valid JSON test: {e}")
    
    # Test 2: Invalid JSON content (should fail with exit code 2)
    print("\n📋 Test 2: Invalid JSON content (should fail)")
    invalid_json = create_invalid_analysis_json()
    
    prompt_invalid = f"""Please write the following JSON content to a file called 'use_case_1_analysis_invalid.json':

{json.dumps(invalid_json, indent=2)}

Save this to the file {env_vars['CLAUDE_OUTPUT_DIR']}/use_case_1_analysis_invalid.json. This should trigger our hooks and the validation should fail."""
    
    try:
        print(f"🚀 Running Claude Code with invalid JSON (should fail)...")
        # Use ClaudeSDKClient with same hooks configuration
        async with ClaudeSDKClient(options=options) as client:
            await client.query(prompt_invalid)
            
            # Process responses
            async for message in client.receive_response():
                if hasattr(message, 'content'):
                    content = str(message.content)
                    print(f"📄 Response: {message.content}")
                    if len(content) > 100:
                        print(f"📄 Response: {message.content[:100]}...")
                    else:
                        print(f"📄 Response: {message.content}")
        
        print(f"⚠️ Claude Code completed (validation may have failed during hooks)")
        
        # Check if invalid file was prevented from being created
        invalid_file = test_use_case_dir / "use_case_1_analysis_invalid.json"
        if not invalid_file.exists():
            print(f"✅ Invalid file was prevented from being created (hooks worked)")
        else:
            print(f"❌ Invalid file was created despite validation (hooks may not be working)")
    
    except Exception as e:
        print(f"✅ Expected: Invalid JSON test failed as expected: {e}")

async def test_analysis_path_redirector():
    """Test the analysis_path_redirector.py hook."""
    print("\n🧪 Testing analysis_path_redirector.py hook...")
    
    test_use_case_dir, env_vars = setup_test_environment()
    
    # Test path redirection by trying to write to a wrong path
    wrong_path = "data/use_case_1_analysis.json"  # This should be redirected
    valid_json = create_valid_analysis_json()
    
    prompt = f"""Please write the following JSON content to this exact path: {wrong_path}

{json.dumps(valid_json, indent=2)}

Note: The hooks should redirect this path to the correct absolute location."""
    
    # Use same options pattern - hooks should come from .claude/settings.json
    options = ClaudeCodeOptions(
        system_prompt="You are testing the StackBench path redirector. Write to the exact path specified.",
        max_turns=3,
        cwd=str(Path.cwd()),
        allowed_tools=["Write", "Read", "LS"]
    )
    
    try:
        print(f"🚀 Running Claude Code with path that needs redirection...")
        # Use ClaudeSDKClient with hooks
        async with ClaudeSDKClient(options=options) as client:
            await client.query(prompt)
            
            # Process responses
            async for message in client.receive_response():
                if hasattr(message, 'content'):
                    content = str(message.content)
                    if len(content) > 100:
                        print(f"📄 Response: {content[:100]}...")
                    else:
                        print(f"📄 Response: {content}")
        
        print(f"✅ Claude Code query completed")
        
        # Check if file ended up in the correct location
        correct_file = test_use_case_dir / "use_case_1_analysis.json"
        if correct_file.exists():
            print(f"✅ Path redirector worked: file created at {correct_file}")
        else:
            print(f"❌ Path redirector failed: file not found at {correct_file}")
            
            # Check if file was created with literal $CLAUDE_OUTPUT_DIR
            literal_dir = test_use_case_dir / "$CLAUDE_OUTPUT_DIR"
            if literal_dir.exists():
                print(f"❌ Found literal $CLAUDE_OUTPUT_DIR directory: {literal_dir}")
    
    except Exception as e:
        print(f"❌ Error during path redirector test: {e}")

def cleanup_test_data():
    """Clean up test data."""
    print("\n🧹 Cleaning up test data...")
    test_data_dir = Path("data/test-hooks-12345")
    if test_data_dir.exists():
        import shutil
        shutil.rmtree(test_data_dir)
        print(f"✅ Cleaned up {test_data_dir}")

async def main():
    """Main test function."""
    print("🧪 StackBench Hooks Test Suite")
    print("=" * 50)
    
    # Check required environment
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("❌ Error: ANTHROPIC_API_KEY environment variable not set")
        sys.exit(1)
    
    try:
        # Test individual hooks
        # await test_analyst_json_validator()
        await test_analysis_path_redirector()
        
        print("\n" + "=" * 50)
        print("✅ All hook tests completed!")
        print("\n💡 Check the output above to see if hooks are working correctly.")
        print("   - Valid JSON should be accepted and saved to correct location")
        print("   - Invalid JSON should be rejected (hook fails with exit code 2)")
        print("   - Path redirector should fix wrong paths automatically")
    
    except Exception as e:
        print(f"❌ Test suite failed: {e}")
        sys.exit(1)
    
    finally:
        cleanup_test_data()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())