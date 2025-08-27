#!/usr/bin/env python3
"""
Claude Code Stop hook to move results.md to the correct output directory for overall analysis.
This hook runs when Claude Code finishes responding to ensure results.md is in the correct location.
"""

import os
import shutil
import sys
from pathlib import Path


def main():
    try:
        # Only run for stackbench_overall_analyzer
        agent = os.getenv('CLAUDE_AGENT', '')
        if agent != 'stackbench_overall_analyzer':
            print(f"[Hook] Skipping - not overall analyzer (agent: '{agent}')", file=sys.stderr)
            sys.exit(0)
        
        output_dir = os.getenv('CLAUDE_OUTPUT_DIR')
        if not output_dir:
            print("[Hook] Warning: No CLAUDE_OUTPUT_DIR found", file=sys.stderr)
            sys.exit(0)
        
        # The expected location for results.md
        expected_path = Path(output_dir) / "results.md"
        
        # Check current working directory for results.md
        cwd_results = Path.cwd() / "results.md"
        if cwd_results.exists():
            if cwd_results.resolve() == expected_path.resolve():
                print(f"[Hook] ✅ results.md already in correct location: {expected_path}", file=sys.stderr)
            else:
                # Move from current working directory to expected location
                try:
                    # Ensure target directory exists
                    expected_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    shutil.move(str(cwd_results), str(expected_path))
                    print(f"[Hook] ✅ Moved results.md from cwd to {expected_path}", file=sys.stderr)
                except Exception as e:
                    print(f"[Hook] ❌ Error moving results.md from cwd: {e}", file=sys.stderr)
                    sys.exit(2)
        elif expected_path.exists():
            print(f"[Hook] ✅ results.md already in correct location: {expected_path}", file=sys.stderr)
        else:
            print("[Hook] No results.md found to move", file=sys.stderr)
        
    except Exception as e:
        print(f"[Hook] Unexpected error: {e}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()