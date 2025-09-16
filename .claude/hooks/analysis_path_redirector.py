#!/usr/bin/env python3
"""
Analysis Path Enforcer Hook for StackBench
Enforces that StackBench analysis JSON files are saved to CLAUDE_OUTPUT_DIR only.
"""

import json
import sys
import os
from pathlib import Path

def main():
    try:
        # Only enforce for StackBench analyzer agent
        claude_agent = os.environ.get('CLAUDE_AGENT', '')
        if claude_agent != 'stackbench_analyzer':
            # Not StackBench - pass through without modification
            tool_data = json.load(sys.stdin)
            json.dump(tool_data, sys.stdout, indent=2)
            sys.exit(0)
        
        # Read the tool data from stdin
        tool_data = json.load(sys.stdin)
        
        # Only process Write operations
        if tool_data.get('tool_name') != 'Write':
            json.dump(tool_data, sys.stdout, indent=2)
            sys.exit(0)
        
        # Get file path from tool input
        tool_input = tool_data.get('tool_input', {})
        file_path = tool_input.get('file_path', '')
        
        if not file_path:
            json.dump(tool_data, sys.stdout, indent=2)
            sys.exit(0)
        
        # Check if this is an analysis JSON file
        filename = os.path.basename(file_path)
        is_analysis_file = (filename.endswith('.json') and 
                           ('analysis' in filename.lower() or 'use_case_' in filename.lower()))
        
        if not is_analysis_file:
            # Not an analysis file - pass through
            json.dump(tool_data, sys.stdout, indent=2)
            sys.exit(0)
        
        print(f"🔧 ANALYSIS PATH ENFORCER: Processing {filename}", file=sys.stderr)
        
        # Get required output directory
        expected_dir = os.environ.get('CLAUDE_OUTPUT_DIR', '')
        if not expected_dir:
            print(f"❌ CLAUDE_OUTPUT_DIR not set - analysis files require this directory", file=sys.stderr)
            sys.exit(2)
        
        # Expand $CLAUDE_OUTPUT_DIR if it appears literally in the path
        if '$CLAUDE_OUTPUT_DIR' in file_path:
            file_path = file_path.replace('$CLAUDE_OUTPUT_DIR', expected_dir)
            print(f"🔄 Expanded $CLAUDE_OUTPUT_DIR to: {file_path}", file=sys.stderr)
            tool_input['file_path'] = file_path
        
        # Ensure the file is being saved to CLAUDE_OUTPUT_DIR
        expected_dir = os.path.abspath(expected_dir)
        file_dir = os.path.dirname(os.path.abspath(file_path))
        
        if file_dir != expected_dir:
            print(f"❌ INVALID PATH: Analysis files must be saved to {expected_dir}", file=sys.stderr)
            print(f"Please save the file to {expected_dir}", file=sys.stderr)
            sys.exit(2)
        
        print(f"✅ Path validated: {filename} -> {expected_dir}", file=sys.stderr)
        
        # Output the potentially modified tool data
        tool_data['tool_input'] = tool_input
        json.dump(tool_data, sys.stdout, indent=2)
        
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON input: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ Path enforcer error: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(2)

if __name__ == "__main__":
    main()