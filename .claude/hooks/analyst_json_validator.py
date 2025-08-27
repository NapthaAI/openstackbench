#!/usr/bin/env python3
"""
StackBench Analysis JSON Validator
Validates that analysis output meets StackBench's required JSON structure.
"""
import json
import sys
import os
from pathlib import Path

# Add the src directory to Python path so we can import our models
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

try:
    from stackbench.analyzers.models import UseCaseAnalysisResult
    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False
    print("⚠️ Could not import Pydantic models, falling back to manual validation", file=sys.stderr)

def show_required_structure():
    """Show the required JSON structure for StackBench analysis output"""
    if PYDANTIC_AVAILABLE:
        return UseCaseAnalysisResult.generate_json_example()
    else:
        # Fallback example for when Pydantic is not available
        example = {
            "use_case_number": 1,
            "use_case_name": "Example Use Case",
            "code_executability": {
                "is_executable": "true/false/\"partial\"",
                "execution_result": "success output or error message",
                "failure_reason": "specific reason if failed",
                "test_results": "additional testing results",
                "failed_due_to_api_key_error": "true/false"
            },
            "underlying_library_usage": {
                "was_used": "true/false",
                "was_mocked": "true/false",
                "mocking_reason": "reason for mocking if applicable",
                "mocking_decision_trace": {
                    "initial_attempts": ["list of initial attempts"],
                    "alternative_approaches": ["list of alternative approaches"],
                    "final_decision_point": "decision reasoning",
                    "mock_strategy": "how mocking was implemented"
                }
            },
            "documentation_tracking": {
                "files_consulted": ["README.md", "docs/api.md"],
                "implementation_notes": ["notes from code comments"],
                "evidence_of_usage": "how documentation was applied"
            },
            "quality_assessment": {
                "completeness_score": "0-10 with reasoning",
                "clarity_score": "0-10 with reasoning", 
                "accuracy_score": "0-10 with reasoning",
                "example_quality_score": "0-10 with reasoning",
                "overall_score": "0-10 overall assessment",
                "agent_readiness": "ready|needs_improvement|not_ready"
            },
            "improvement_recommendations": [
                {
                    "priority": "critical|high|medium|low",
                    "category": "missing_info|unclear_explanation|poor_examples|structure",
                    "issue": "specific problem identified",
                    "recommendation": "specific improvement needed",
                    "expected_impact": "how this would help future agents"
                }
            ]
        }
        return json.dumps(example, indent=2)

def validate_stackbench_json_structure(data, filename):
    """Validate StackBench analysis JSON structure using Pydantic."""
    if PYDANTIC_AVAILABLE:
        try:
            # Use Pydantic to validate the entire structure
            result = UseCaseAnalysisResult.model_validate(data)
            return True, []
        except Exception as e:
            # Pydantic validation failed
            error_msg = str(e)
            # Make Pydantic errors more user-friendly
            if "validation error" in error_msg.lower():
                return False, [f"Pydantic validation failed: {error_msg}"]
            else:
                return False, [f"JSON structure validation failed: {error_msg}"]
    else:
        # Fallback to manual validation when Pydantic is not available
        return validate_stackbench_json_structure_manual(data, filename)

def validate_stackbench_json_structure_manual(data, filename):
    """Manual validation fallback when Pydantic is not available."""
    errors = []
    
    # Required top-level keys for StackBench
    required_keys = [
        "use_case_number", "use_case_name", "code_executability",
        "underlying_library_usage", "documentation_tracking",
        "quality_assessment", "improvement_recommendations"
    ]
    
    for key in required_keys:
        if key not in data:
            errors.append(f"Missing required top-level key: '{key}'")
    
    # Validate is_executable supports "partial"
    if "code_executability" in data:
        exec_data = data["code_executability"]
        if "is_executable" in exec_data:
            is_exec = exec_data["is_executable"]
            if not (isinstance(is_exec, bool) or is_exec == "partial"):
                errors.append("'is_executable' should be true, false, or \"partial\"")
    
    # Basic required field validation
    if "code_executability" in data:
        exec_fields = ["is_executable", "execution_result", "failed_due_to_api_key_error"]
        for field in exec_fields:
            if field not in data["code_executability"]:
                errors.append(f"Missing '{field}' in 'code_executability'")
    
    return len(errors) == 0, errors

def validate_file_location(file_path):
    """Validate that the analysis file is being saved in the correct location."""
    expected_dir = os.environ.get('CLAUDE_OUTPUT_DIR', '')
    if not expected_dir:
        print("⚠️ No CLAUDE_OUTPUT_DIR set, cannot validate file location", file=sys.stderr)
        return True
    
    file_dir = os.path.dirname(os.path.abspath(file_path))
    expected_dir = os.path.abspath(expected_dir)
    
    if file_dir != expected_dir:
        print(f"❌ WRONG LOCATION: File being saved in wrong directory!", file=sys.stderr)
        print(f"   Expected: {expected_dir}", file=sys.stderr)
        print(f"   Actual:   {file_dir}", file=sys.stderr)
        print(f"💡 Use absolute path: {expected_dir}/{os.path.basename(file_path)}", file=sys.stderr)
        return False
    else:
        print(f"✅ CORRECT LOCATION: File being saved in expected directory", file=sys.stderr)
        print(f"   Directory: {file_dir}", file=sys.stderr)
        return True

def main():
    try:
        # Only run for StackBench analyzer agent
        claude_agent = os.environ.get('CLAUDE_AGENT', '')
        if claude_agent != 'stackbench_analyzer':
            print(f"⏭️ Skipping validation - not StackBench analyzer (agent: '{claude_agent}')", file=sys.stderr)
            sys.exit(0)
        
        print("🔧 STACKBENCH JSON VALIDATOR: Starting validation", file=sys.stderr)
        tool_data = json.load(sys.stdin)
        file_path = tool_data.get('tool_input', {}).get('file_path', '')
        
        if not file_path:
            print("⏭️ No file path in tool input, skipping.", file=sys.stderr)
            sys.exit(0)
        
        filename = os.path.basename(file_path)
        print(f"📁 Processing file: {filename}", file=sys.stderr)
        
        if not (filename.endswith('.json') and ('analysis' in filename.lower() or 'use_case_' in filename.lower())):
            print("⏭️ Not a StackBench analysis file, skipping validation.", file=sys.stderr)
            sys.exit(0)
        
        # Validate file location first
        if not validate_file_location(file_path):
            print("❌ File location validation failed. Fix the path and try again.", file=sys.stderr)
            sys.exit(1)
        
        if not tool_data.get('tool_response', {}).get('success', False):
            print("⚠️ Write marked as failed, but checking if file exists anyway.", file=sys.stderr)
        
        if not os.path.exists(file_path):
            print(f"❌ File {file_path} does not exist. Validation failed.", file=sys.stderr)
            sys.exit(1)
        
        print(f"📖 Reading and validating StackBench analysis JSON: {filename}", file=sys.stderr)
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                file_content = json.load(f)
        except json.JSONDecodeError as e:
            print(f"❌ INVALID JSON in {filename}: {e}", file=sys.stderr)
            print("💡 Fix JSON syntax and try again.", file=sys.stderr)
            sys.exit(2)
        
        is_valid, errors = validate_stackbench_json_structure(file_content, filename)
        
        if is_valid:
            print(f"✅ {filename} STACKBENCH JSON STRUCTURE IS VALID", file=sys.stderr)
            try:
                use_case_number = file_content.get("use_case_number", "N/A")
                is_executable = file_content.get("code_executability", {}).get("is_executable")
                was_mocked = file_content.get("underlying_library_usage", {}).get("was_mocked")
                files_consulted = file_content.get("documentation_tracking", {}).get("files_consulted", [])
                overall_score = file_content.get("quality_assessment", {}).get("overall_score", "N/A")
                
                # Handle partial executable status
                exec_status = is_executable
                if exec_status == "partial":
                    exec_status = "PARTIAL"
                elif exec_status is True:
                    exec_status = "YES"
                elif exec_status is False:
                    exec_status = "NO"
                else:
                    exec_status = str(exec_status)
                    
                print(f"📊 Use Case {use_case_number}: Executable={exec_status}, Mocked={was_mocked}, DocsUsed={len(files_consulted)}, Score='{overall_score}'", file=sys.stderr)
            except Exception as e:
                print(f"Could not print stats due to an error: {e}", file=sys.stderr)
        else:
            print(f"❌ STACKBENCH JSON VALIDATION FAILED for {filename}:", file=sys.stderr)
            for error in errors:
                print(f"   • {error}", file=sys.stderr)
            print("\n🔧 Fix these issues and rewrite the file.", file=sys.stderr)
            print("\n📋 REQUIRED STRUCTURE - Here's how a valid StackBench analysis JSON should look:", file=sys.stderr)
            print(show_required_structure(), file=sys.stderr)
            sys.exit(2)
            
        print("✅ StackBench JSON validation complete.", file=sys.stderr)
            
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON input to hook: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ StackBench JSON validation hook error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()