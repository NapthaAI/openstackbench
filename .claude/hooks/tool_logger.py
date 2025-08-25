#!/usr/bin/env python3
"""
Tool Logger for Documentation Readiness Testing
Logs all tool inputs and outputs for execution agent and analyst agent analysis.
"""

import json
import sys
import os
import datetime

def setup_logging():
    """Ensure log directory exists."""
    log_dir = os.environ.get('CLAUDE_LOGS_DIR', os.getcwd())
    os.makedirs(log_dir, exist_ok=True)
    return log_dir

def get_log_filename(event_type, log_dir):
    """Generate log filename with use case ID if available."""
    use_case_id = os.environ.get('CLAUDE_USE_CASE_ID', 'unknown')
    agent = os.environ.get('CLAUDE_AGENT', 'unknown')
    return os.path.join(log_dir, f"{event_type.lower()}_{use_case_id}_{agent}.jsonl")

def log_tool_event(event_type, data):
    """Log tool event to file."""
    log_dir = setup_logging()
    
    # Create log entry with timestamp and raw data
    log_entry = {
        "timestamp": datetime.datetime.now().isoformat(),
        "event_type": event_type,
        "use_case_id": os.environ.get('CLAUDE_USE_CASE_ID', 'unknown'),
        "programming_language": os.environ.get('CLAUDE_USE_CASE_PROGRAMMING_LANGUAGE', 'unknown'),
        "raw_data": data
    }
    
    # Write to log file
    log_filename = get_log_filename(event_type, log_dir)
    try:
        with open(log_filename, 'a') as f:
            f.write(json.dumps(log_entry, default=str) + '\n')
    except Exception as e:
        print(f"Logging error: {e}", file=sys.stderr)

def log_pretooluse():
    """Log PreToolUse event."""
    try:
        input_data = json.load(sys.stdin)
        
        # Log the raw data
        log_tool_event("PreToolUse", input_data)
        
        # Simple output for transcript
        tool_name = input_data.get("tool_name", "unknown")
        if tool_name == "Read":
            file_path = input_data.get("tool_input", {}).get("file_path", "unknown")
            print(f"📖 Reading: {file_path}", file=sys.stderr)
        elif tool_name == "Write":
            file_path = input_data.get("tool_input", {}).get("file_path", "unknown")
            print(f"✍️ Writing: {file_path}", file=sys.stderr)
        elif tool_name == "Edit":
            file_path = input_data.get("tool_input", {}).get("file_path", "unknown")
            print(f"✏️ Editing: {file_path}", file=sys.stderr)
        elif tool_name == "Bash":
            command = input_data.get("tool_input", {}).get("command", "unknown")
            print(f"💻 Executing: {command[:50]}...", file=sys.stderr)
        elif tool_name == "Grep":
            pattern = input_data.get("tool_input", {}).get("pattern", "unknown")
            print(f"🔍 Searching: {pattern}", file=sys.stderr)
        elif tool_name == "Glob":
            pattern = input_data.get("tool_input", {}).get("pattern", "unknown")
            print(f"📁 Finding: {pattern}", file=sys.stderr)
        else:
            print(f"🔧 {tool_name}: executing", file=sys.stderr)
        
    except Exception as e:
        print(f"Tool logging error: {e}", file=sys.stderr)

def log_posttooluse():
    """Log PostToolUse event."""
    try:
        input_data = json.load(sys.stdin)
        
        # Log the raw data
        log_tool_event("PostToolUse", input_data)
        
        # Simple output for transcript
        tool_name = input_data.get("tool_name", "unknown")
        success = input_data.get("tool_response", {}).get("success", False)
        status = "✅" if success else "❌"
        print(f"{status} {tool_name} completed", file=sys.stderr)
        
    except Exception as e:
        print(f"Tool logging error: {e}", file=sys.stderr)

def main():
    """Main entry point - determine which hook is being called."""
    # Only run tool logger if agent is stackbench_analyzer
    agent = os.environ.get('CLAUDE_AGENT', 'unknown')
    if agent != 'stackbench_analyzer':
        # Exit silently for non-stackbench agents
        sys.exit(0)
    
    hook_type = os.environ.get('CLAUDE_HOOK_TYPE', 'PreToolUse')
    
    if len(sys.argv) > 1:
        hook_type = sys.argv[1]
    
    if hook_type == "PreToolUse":
        log_pretooluse()
    elif hook_type == "PostToolUse":
        log_posttooluse()
    else:
        print(f"Unknown hook type: {hook_type}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()