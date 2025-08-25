#!/usr/bin/env python3
"""
Claude Code hook to move results.md to the correct output directory for overall analysis.
This hook runs after Claude Code completes its response for overall analysis.
"""

import os
import shutil
from pathlib import Path


def main():
    # Check if this is an overall analysis session
    agent = os.getenv('CLAUDE_AGENT', '')
    if agent != 'stackbench_overall_analyzer':
        return  # Only run for overall analysis
    
    output_dir = os.getenv('CLAUDE_OUTPUT_DIR')
    if not output_dir:
        print("[Hook] No CLAUDE_OUTPUT_DIR found")
        return
    
    # Check if results.md was created in current working directory
    cwd = Path.cwd()
    results_md_cwd = cwd / "results.md"
    
    if results_md_cwd.exists():
        target_path = Path(output_dir) / "results.md"
        
        try:
            # Move the file to the correct location
            shutil.move(str(results_md_cwd), str(target_path))
            print(f"[Hook] Moved results.md from {results_md_cwd} to {target_path}")
        except Exception as e:
            print(f"[Hook] Error moving results.md: {e}")
    else:
        print("[Hook] No results.md found in current directory")


if __name__ == "__main__":
    main()