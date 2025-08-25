#!/usr/bin/env python3
"""
StackBench Analysis JSON Validator
Validates that analysis output meets StackBench's required JSON structure.
"""
import json
import sys
import os

def show_required_structure():
    """Show the required JSON structure for StackBench analysis output"""
    example = {
        "use_case_number": 1,
        "use_case_name": "Example Use Case",
        "code_executability": {
            "is_executable": True,
            "execution_result": "success output or error message",
            "failure_reason": "specific reason if failed",
            "test_results": "additional testing results",
            "failed_due_to_api_key_error": False
        },
        "underlying_library_usage": {
            "was_used": True,
            "was_mocked": False,
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
    """Validate StackBench analysis JSON structure."""
    errors = []
    
    # Required top-level keys for StackBench
    required_keys = [
        "use_case_number",
        "use_case_name", 
        "code_executability",
        "underlying_library_usage",
        "documentation_tracking",
        "quality_assessment",
        "improvement_recommendations"
    ]
    
    for key in required_keys:
        if key not in data:
            errors.append(f"Missing required top-level key: '{key}'")
    
    # Basic type checking
    expected_types = {
        "use_case_number": int,
        "use_case_name": str,
        "code_executability": dict,
        "underlying_library_usage": dict,
        "documentation_tracking": dict,
        "quality_assessment": dict,
        "improvement_recommendations": list
    }
    
    for key, expected_type in expected_types.items():
        if key in data and not isinstance(data[key], expected_type):
            errors.append(f"'{key}' should be {expected_type.__name__}, got {type(data[key]).__name__}")
    
    # Validate code_executability structure
    if "code_executability" in data and isinstance(data.get("code_executability"), dict):
        exec_data = data["code_executability"]
        required_exec_fields = ["is_executable", "failed_due_to_api_key_error"]
        for field in required_exec_fields:
            if field not in exec_data:
                errors.append(f"Missing '{field}' in 'code_executability'")
            elif not isinstance(exec_data.get(field), bool):
                errors.append(f"'{field}' should be boolean in 'code_executability'")

    # Validate underlying_library_usage structure  
    if "underlying_library_usage" in data and isinstance(data.get("underlying_library_usage"), dict):
        lib_usage = data["underlying_library_usage"]
        required_lib_fields = ["was_used", "was_mocked"]
        for field in required_lib_fields:
            if field not in lib_usage:
                errors.append(f"Missing '{field}' in 'underlying_library_usage'")
            elif not isinstance(lib_usage.get(field), bool):
                errors.append(f"'{field}' should be boolean in 'underlying_library_usage'")
        
        # Validate mocking_decision_trace if present (optional)
        if "mocking_decision_trace" in lib_usage:
            trace = lib_usage["mocking_decision_trace"]
            if not isinstance(trace, dict):
                errors.append("'mocking_decision_trace' should be an object")

    # Validate documentation_tracking structure
    if "documentation_tracking" in data and isinstance(data.get("documentation_tracking"), dict):
        doc_tracking = data["documentation_tracking"]
        if "files_consulted" in doc_tracking and not isinstance(doc_tracking.get("files_consulted"), list):
            errors.append("'files_consulted' should be an array in 'documentation_tracking'")
        if "implementation_notes" in doc_tracking and not isinstance(doc_tracking.get("implementation_notes"), list):
            errors.append("'implementation_notes' should be an array in 'documentation_tracking'")
    
    # Validate quality_assessment structure
    if "quality_assessment" in data and isinstance(data.get("quality_assessment"), dict):
        quality = data["quality_assessment"]
        required_quality_fields = ["completeness_score", "clarity_score", "accuracy_score",
                                 "example_quality_score", "overall_score", "agent_readiness"]
        for field in required_quality_fields:
            if field not in quality:
                errors.append(f"Missing '{field}' in 'quality_assessment'")
    
    # Validate improvement_recommendations structure
    if "improvement_recommendations" in data and isinstance(data.get("improvement_recommendations"), list):
        for i, rec in enumerate(data["improvement_recommendations"]):
            if not isinstance(rec, dict):
                errors.append(f"improvement_recommendations[{i}] should be an object")
            else:
                required_rec_fields = ["priority", "category", "issue", "recommendation", "expected_impact"]
                for field in required_rec_fields:
                    if field not in rec:
                        errors.append(f"Missing '{field}' in improvement_recommendations[{i}]")
    
    return len(errors) == 0, errors

def main():
    try:
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
                
                print(f"📊 Use Case {use_case_number}: Executable={is_executable}, Mocked={was_mocked}, DocsUsed={len(files_consulted)}, Score='{overall_score}'", file=sys.stderr)
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