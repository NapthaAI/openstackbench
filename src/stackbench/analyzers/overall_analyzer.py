"""Overall analyzer for aggregating individual use case results into final report."""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

from claude_code_sdk import ClaudeSDKClient, ClaudeCodeOptions

from ..config import get_config
from ..core.run_context import RunContext


class OverallAnalyzer:
    """Simple analyzer for generating overall results from individual use case analyses."""
    
    def __init__(self, config: Optional[Dict] = None, verbose: bool = False):
        self.config = get_config()
        self.verbose = verbose
        if config:
            # Override config values if provided
            for key, value in config.items():
                if hasattr(self.config, key):
                    setattr(self.config, key, value)
    
    def generate_results_json(self, run_id: str) -> Dict[str, Any]:
        """Generate deterministic results.json by aggregating individual analysis files."""
        
        try:
            context = RunContext.load(run_id)
        except Exception as e:
            raise ValueError(f"Could not load run context: {e}")
        
        # Load individual analysis results
        individual_results = self._load_individual_results(context)
        
        if not individual_results:
            raise ValueError("No individual analysis results found to aggregate")
        
        # Calculate detailed metrics
        total_cases = len(individual_results)
        successful_cases_score = self._count_successful_cases(individual_results)
        
        # Count individual categories for better reporting
        full_successes = sum(1 for result in individual_results 
                           if result.get("code_executability", {}).get("is_executable") in [True, "true"])
        partial_successes = sum(1 for result in individual_results 
                              if result.get("code_executability", {}).get("is_executable") == "partial")
        failures = total_cases - full_successes - partial_successes
        
        success_rate = (successful_cases_score / total_cases * 100) if total_cases > 0 else 0.0
        
        # Determine pass/fail status (using 50% threshold)
        pass_fail_status = "PASS" if success_rate >= 50.0 else "FAIL"
        
        # Structure results
        results = {
            "run_id": run_id,
            "repository": {
                "name": context.repo_name,
                "url": context.config.repo_url
            },
            "analysis_metadata": {
                "analyzed_at": datetime.now().isoformat(),
                "analyzer_version": "1.0.0",
                "total_results": len(individual_results)
            },
            "overall_summary": {
                "pass_fail_status": pass_fail_status,
                "success_rate": success_rate,
                "total_use_cases": total_cases,
                "full_successes": full_successes,
                "partial_successes": partial_successes,
                "failures": failures,
                "success_score": successful_cases_score
            },
            "use_case_results": individual_results
        }
        
        return results
    
    def save_results_json(self, run_id: str, results_path: Optional[Path] = None) -> Path:
        """Generate and save results.json file."""
        
        if results_path is None:
            context = RunContext.load(run_id)
            results_path = context.run_dir / "results.json"
        
        results = self.generate_results_json(run_id)
        
        with open(results_path, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        if self.verbose:
            print(f"[OverallAnalyzer] Saved results.json to: {results_path}")
        
        return results_path
    
    async def generate_results_markdown(self, run_id: str) -> str:
        """Generate results.md using Claude Code analysis of the unified JSON data."""
        
        try:
            context = RunContext.load(run_id)
        except Exception as e:
            raise ValueError(f"Could not load run context: {e}")
        
        # Generate the unified results JSON
        results_json = self.generate_results_json(run_id)
        
        # Create analysis prompt for Claude Code
        prompt = self._create_markdown_analysis_prompt(results_json, context)
        
        # Set up Claude Code client environment
        results_dir = context.run_dir
        logs_dir = results_dir / "logs" / "overall_analysis"
        logs_dir.mkdir(parents=True, exist_ok=True)
        
        os.environ['CLAUDE_USE_CASE_ID'] = 'overall_analysis'
        os.environ['CLAUDE_OUTPUT_DIR'] = str(results_dir.absolute())
        os.environ['CLAUDE_LOGS_DIR'] = str(logs_dir.absolute())
        os.environ['CLAUDE_PROJECT_DIR'] = str(Path.cwd().absolute())
        os.environ['CLAUDE_AGENT'] = 'stackbench_overall_analyzer'
        
        # Set up Claude Code options
        options = ClaudeCodeOptions(
            system_prompt="You are an expert at analyzing coding agent benchmark results and generating comprehensive analysis reports.",
            max_turns=self.config.analysis_max_turns,
            cwd=str(Path.cwd()),
            allowed_tools=["Read", "Write", "Bash", "LS", "Grep"]
        )
        
        if self.verbose:
            print(f"[OverallAnalyzer] Starting markdown report generation for {context.repo_name}")
            print(f"[OverallAnalyzer] Output directory: {results_dir}")
        
        # Generate report using Claude Code
        try:
            async with ClaudeSDKClient(options=options) as client:
                await client.query(prompt)
                
                # Process the response and save messages for debugging
                messages = []
                async for message in client.receive_response():
                    messages.append(message)
                    if self.verbose:
                        print(f"[OverallAnalyzer] Received response message")
                
                # Save analysis messages for debugging
                try:
                    from .individual_analyzer import IndividualAnalyzer
                    analyzer = IndividualAnalyzer()
                    messages_dict = analyzer.messages_to_dict(messages)
                    analysis_messages_path = logs_dir / "overall_analysis_messages.json"
                    import json
                    with open(analysis_messages_path, 'w') as f:
                        json.dump(messages_dict, f, indent=2, default=str)
                    if self.verbose:
                        print(f"[OverallAnalyzer] Saved analysis messages to: {analysis_messages_path}")
                except Exception as e:
                    print(f"[OverallAnalyzer] Warning: Could not save analysis messages: {e}")
                
                # Check if results.md was created (should be moved by hook)
                results_md_path = results_dir / "results.md"
                if results_md_path.exists():
                    with open(results_md_path, 'r') as f:
                        markdown_content = f.read()
                    
                    if self.verbose:
                        print(f"[OverallAnalyzer] Successfully generated results.md")
                    
                    return markdown_content
                else:
                    raise ValueError("Claude Code did not generate results.md file")
                    
        except Exception as e:
            raise ValueError(f"Failed to generate markdown report: {e}")
    
    async def save_results_markdown(self, run_id: str, markdown_path: Optional[Path] = None) -> Path:
        """Generate and save results.md file."""
        
        if markdown_path is None:
            context = RunContext.load(run_id)
            markdown_path = context.run_dir / "results.md"
        
        markdown_content = await self.generate_results_markdown(run_id)
        
        with open(markdown_path, 'w') as f:
            f.write(markdown_content)
        
        if self.verbose:
            print(f"[OverallAnalyzer] Saved results.md to: {markdown_path}")
        
        return markdown_path
    
    async def analyze_run(self, run_id: str) -> Dict[str, Path]:
        """Generate both results.json and results.md for a run."""
        
        if self.verbose:
            print(f"[OverallAnalyzer] Starting overall analysis for run {run_id}")
        
        # Generate results.json (deterministic)
        json_path = self.save_results_json(run_id)
        
        # Generate results.md (using Claude Code)
        markdown_path = await self.save_results_markdown(run_id)
        
        if self.verbose:
            print(f"[OverallAnalyzer] Completed overall analysis for run {run_id}")
        
        return {
            "results_json": json_path,
            "results_markdown": markdown_path
        }
    
    def _load_individual_results(self, context: RunContext) -> List[Dict[str, Any]]:
        """Load all individual use case analysis results."""
        results = []
        
        # Scan for use case analysis files
        for use_case_num in range(1, context.status.total_use_cases + 1):
            use_case_dir = context.data_dir / f"use_case_{use_case_num}"
            analysis_file = use_case_dir / f"use_case_{use_case_num}_analysis.json"
            
            if analysis_file.exists():
                try:
                    with open(analysis_file, 'r') as f:
                        result = json.load(f)
                    results.append(result)
                    if self.verbose:
                        print(f"[OverallAnalyzer] Loaded analysis for use case {use_case_num}")
                except Exception as e:
                    if self.verbose:
                        print(f"[OverallAnalyzer] Warning: Could not load analysis for use case {use_case_num}: {e}")
                    continue
            else:
                if self.verbose:
                    print(f"[OverallAnalyzer] Warning: Analysis file not found for use case {use_case_num}")
        
        return results
    
    def _count_successful_cases(self, results: List[Dict[str, Any]]) -> float:
        """Count successful use cases from results, with partial = 0.5 points."""
        successful_cases = 0.0
        
        for result in results:
            # Check if the use case was executable (including partial)
            code_exec = result.get("code_executability", {})
            is_executable = code_exec.get("is_executable", False)
            # Handle both boolean and string representations
            if is_executable in [True, "true"]:
                successful_cases += 1.0  # Full success
            elif is_executable == "partial":
                successful_cases += 0.5  # Partial success
        
        return successful_cases
    
    def _create_markdown_analysis_prompt(self, results_json: Dict[str, Any], context: RunContext) -> str:
        """Create analysis prompt for Claude Code to generate markdown report."""
        
        # Extract key information for the prompt
        repo_name = results_json["repository"]["name"]
        overall_summary = results_json["overall_summary"]
        pass_fail = overall_summary["pass_fail_status"]
        success_rate = overall_summary["success_rate"]
        total_cases = overall_summary["total_use_cases"]
        full_successes = overall_summary["full_successes"]
        partial_successes = overall_summary["partial_successes"]
        failures = overall_summary["failures"]
        success_score = overall_summary["success_score"]
        
        # Create a summary of individual results for analysis
        use_case_summaries = []
        for result in results_json["use_case_results"]:
            use_case_name = result.get("use_case_name", "Unknown")
            use_case_num = result.get("use_case_number", "?")
            is_executable = result.get("code_executability", {}).get("is_executable", False)
            failure_reason = result.get("code_executability", {}).get("failure_reason", "")
            lib_used = result.get("underlying_library_usage", {}).get("was_used", False)
            lib_mocked = result.get("underlying_library_usage", {}).get("was_mocked", False)
            
            use_case_summaries.append({
                "number": use_case_num,
                "name": use_case_name,
                "executable": is_executable,
                "failure_reason": failure_reason,
                "library_used": lib_used,
                "library_mocked": lib_mocked
            })
        
        prompt = f"""# StackBench Overall Analysis Report Generation

You are analyzing the results of a StackBench coding agent benchmark run. Your task is to generate a comprehensive analysis report in markdown format.

## Benchmark Results Data

**Repository**: {repo_name}
**Overall Status**: {pass_fail}  
**Success Rate**: {success_rate:.1f}% (Score: {success_score:.1f}/{total_cases})
**Breakdown**: {full_successes} full successes, {partial_successes} partial successes, {failures} failures

## Individual Use Case Results Summary

"""
        
        for uc in use_case_summaries:
            if uc["executable"] in [True, "true"]:
                status = "✅ FULL SUCCESS"
            elif uc["executable"] == "partial":
                status = "🔶 PARTIAL SUCCESS"
            else:
                status = "❌ FAILURE"
                
            lib_info = ""
            if uc["library_used"]:
                lib_info += " | Real library used"
            if uc["library_mocked"]:
                lib_info += " | Library mocked"
            
            prompt += f"- **Use Case {uc['number']}**: {uc['name']} - {status}{lib_info}\n"
            if uc["failure_reason"]:
                prompt += f"  - Issue: {uc['failure_reason']}\n"
        
        prompt += f"""

## Full Results JSON Data

Here is the complete results data for detailed analysis:

```json
{json.dumps(results_json, indent=2, default=str)}
```

## Task: Generate Analysis Report

Create a comprehensive analysis report as `results.md` following this structure:

```markdown
# {repo_name} Analysis Report

**Pass/Fail Status:** {pass_fail}
**Success Rate:** {success_score:.1f}/{total_cases} tasks successful ({success_rate:.1f}%)

## Executive Summary
[Provide 2-3 sentences summarizing the overall performance and key findings]

## Common Failures Analysis
[Analyze the failure patterns across use cases. Look for:]
- Recurring error types or failure reasons
- Library usage challenges (mocking vs real usage)
- Documentation gaps that affected multiple use cases
- Provide specific examples from the failed use cases

## Framework-Specific Insights  
[Provide insights about the library/framework based on the results:]
- Library API accessibility and usability
- Documentation quality assessment
- Patterns that suggest systematic issues
- Recommendations for library maintainers

## Use Case Results Details
[Create a table or list showing each use case result with key details]

## Recommendations
[Specific actionable recommendations based on the analysis]
```

**Important Requirements:**
1. Save the analysis report to `results.md` in the run directory: {str(context.run_dir.resolve() / "results.md")}
2. Focus on actionable insights that would help library maintainers improve AI agent compatibility
3. Use specific examples from the results data to support your analysis
4. Keep the tone professional and constructive
5. Highlight both successes and failures to provide balanced feedback

Generate the analysis report now by creating the `results.md` file at the specified path.
"""
        
        return prompt