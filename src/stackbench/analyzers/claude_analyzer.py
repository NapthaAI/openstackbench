"""Claude Code analyzer for StackBench implementation analysis."""

import asyncio
import json
import os
from pathlib import Path
from typing import Dict, List, Optional

from claude_code_sdk import ClaudeSDKClient, ClaudeCodeOptions

from ..config import get_config
from ..core.run_context import RunContext
from ..extractors.models import UseCase
from ..extractors.extractor import load_use_cases
from .models import (
    CodeExecutabilityResult,
    UnderlyingLibraryUsage, 
    MockingAnalysis,
    MockingDecisionTrace,
    QualityAssessment,
    ImprovementRecommendation,
    OverallSummary,
    CommonFailurePattern,
    FrameworkInsight
)


class ClaudeAnalyzer:
    """Claude Code-powered analyzer for use case implementations."""
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = get_config()
        if config:
            # Override config values if provided
            for key, value in config.items():
                if hasattr(self.config, key):
                    setattr(self.config, key, value)
    
    def create_analysis_prompt(
        self, 
        use_case: UseCase, 
        use_case_number: int, 
        context: RunContext,
        target_file_path: Path
    ) -> str:
        """Create comprehensive analysis prompt for Claude Code."""
        
        # Get relative paths for cleaner display
        try:
            relative_repo_dir = context.repo_dir.relative_to(Path.cwd())
        except ValueError:
            relative_repo_dir = context.repo_dir
            
        try:
            relative_target_file = target_file_path.relative_to(Path.cwd())
        except ValueError:
            relative_target_file = target_file_path
        
        prompt = f"""# StackBench Analysis: Use Case {use_case_number}

You are a documentation analysis expert specializing in evaluating how effectively coding agents implement library-specific tasks.

## Your Mission
Analyze the implementation to assess documentation quality and provide structured analysis in JSON format.

## Use Case That Was Implemented
**Name:** {use_case.name}
**Elevator Pitch:** {use_case.elevator_pitch}
**Target Audience:** {use_case.target_audience}
**Complexity Level:** {use_case.complexity_level}
**Real-world Scenario:** {use_case.real_world_scenario}

**Functional Requirements:**
"""
        for i, req in enumerate(use_case.functional_requirements, 1):
            prompt += f"{i}. {req}\n"
        
        prompt += f"""
**User Stories:**
"""
        for i, story in enumerate(use_case.user_stories, 1):
            prompt += f"{i}. {story}\n"
        
        prompt += f"""
**System Design:** {use_case.system_design}
**Architecture Pattern:** {use_case.architecture_pattern}

## Implementation to Analyze
**Repository Path:** `{relative_repo_dir}`
**Implementation File:** `{relative_target_file}`

## Analysis Process

### Step 1: Read Implementation
Use the Read tool to examine the implementation file. Look for:
- Documentation tracking comments at the top
- Import statements and library usage
- Implementation approach and patterns
- Error handling and edge cases

### Step 2: Test Code Executability  
**IMPORTANT:** Test the implementation by running it exactly as written. Do NOT modify the code.
- You may set environment variables if needed (e.g., export API_KEY=test)
- You may install dependencies if needed
- Capture success output or error messages
- Assess code quality and functionality

### Step 3: Analyze Library Usage
Determine if the implementation uses:
- Real library imports and methods
- Mock/fake implementations
- If mocked, try to understand why from the code comments and structure

### Step 4: Documentation Analysis
Since IDE agents don't have tool usage logs, analyze documentation usage from:
- "DOCUMENTATION CONSULTED" comments in the implementation
- Quality of implementation patterns used
- Evidence of following library conventions

## Required JSON Output
Save your analysis as a JSON file with this structure:

```json
{{
  "use_case_number": {use_case_number},
  "use_case_name": "{use_case.name}",
  "code_executability": {{
    "is_executable": true/false,
    "execution_result": "Success output or error message",
    "failure_reason": "Specific reason if failed",
    "test_results": "Additional testing results",
    "failed_due_to_api_key_error": true/false
  }},
  "underlying_library_usage": {{
    "was_used": true/false,
    "was_mocked": true/false,
    "mocking_reason": "Why mocking was chosen if applicable",
    "mocking_decision_trace": {{
      "initial_attempts": [],
      "alternative_approaches": [],
      "final_decision_point": "Decision reasoning",
      "mock_strategy": "How mocking was implemented"
    }}
  }},
  "documentation_tracking": {{
    "files_consulted": ["list of files from comments"],
    "implementation_notes": ["notes from code comments"],
    "evidence_of_usage": "How docs were applied in implementation"
  }},
  "quality_assessment": {{
    "completeness_score": "0-10 with reasoning",
    "clarity_score": "0-10 with reasoning", 
    "accuracy_score": "0-10 with reasoning",
    "example_quality_score": "0-10 with reasoning",
    "overall_score": "0-10 overall assessment",
    "agent_readiness": "ready|needs_improvement|not_ready"
  }},
  "improvement_recommendations": [
    {{
      "priority": "critical|high|medium|low",
      "category": "missing_info|unclear_explanation|poor_examples|structure",
      "issue": "Specific problem identified",
      "recommendation": "Specific improvement needed",
      "expected_impact": "How this would help future agents"
    }}
  ]
}}
```

**Save the analysis to:** `{relative_target_file.parent}/use_case_{use_case_number}_analysis.json`
"""
        return prompt
    
    async def analyze_use_case(
        self,
        run_id: str,
        use_case_number: int,
        use_case: UseCase,
        context: RunContext
    ) -> Dict:
        """Analyze a single use case implementation."""
        
        # Determine target file path
        use_case_dir = context.data_dir / f"use_case_{use_case_number}"
        target_file_path = use_case_dir / use_case.target_file
        
        if not target_file_path.exists():
            return {
                "use_case_number": use_case_number,
                "use_case_name": use_case.name,
                "error": f"Implementation file not found: {target_file_path}",
                "code_executability": {
                    "is_executable": False,
                    "execution_result": "File not found",
                    "failure_reason": "Implementation file missing",
                    "failed_due_to_api_key_error": False
                }
            }
        
        # Create analysis prompt
        prompt = self.create_analysis_prompt(
            use_case=use_case,
            use_case_number=use_case_number,
            context=context,
            target_file_path=target_file_path
        )
        
        # Set up Claude Code client
        options = ClaudeCodeOptions(
            system_prompt="You are a documentation analysis expert. Analyze implementations systematically and provide structured JSON output.",
            max_turns=self.config.analysis_max_turns,
            cwd=str(context.repo_dir),  # Run analysis from repository directory
            allowed_tools=["Read", "Write", "Bash", "LS", "Grep"]
        )
        
        try:
            async with ClaudeSDKClient(options=options) as client:
                await client.query(prompt)
                
                # Collect analysis result
                analysis_text = []
                async for message in client.receive_response():
                    if hasattr(message, 'content'):
                        for block in message.content:
                            if hasattr(block, 'text'):
                                analysis_text.append(block.text)
                
                # Try to read the generated analysis file
                analysis_file = use_case_dir / f"use_case_{use_case_number}_analysis.json"
                if analysis_file.exists():
                    with open(analysis_file, 'r') as f:
                        return json.load(f)
                else:
                    # Fallback: try to extract JSON from response text
                    full_text = ''.join(analysis_text)
                    # Look for JSON blocks in the response
                    import re
                    json_match = re.search(r'```json\s*(\{.*?\})\s*```', full_text, re.DOTALL)
                    if json_match:
                        return json.loads(json_match.group(1))
                    else:
                        return {
                            "use_case_number": use_case_number,
                            "use_case_name": use_case.name,
                            "error": "Could not extract JSON analysis from response",
                            "raw_response": full_text[:1000]  # First 1000 chars for debugging
                        }
                        
        except Exception as e:
            return {
                "use_case_number": use_case_number,
                "use_case_name": use_case.name,
                "error": f"Analysis failed: {str(e)}",
                "code_executability": {
                    "is_executable": False,
                    "execution_result": f"Analysis error: {str(e)}",
                    "failure_reason": "Analysis process failed",
                    "failed_due_to_api_key_error": "ANTHROPIC_API_KEY" in str(e)
                }
            }
    
    async def analyze_run(self, run_id: str, max_workers: int = 3) -> Dict:
        """Analyze all use cases in a benchmark run with parallel processing."""
        
        try:
            context = RunContext.load(run_id)
        except Exception as e:
            raise ValueError(f"Could not load run context: {e}")
        
        # Validate run phase
        if context.status.phase not in ["extracted", "executed", "analyzed"]:
            raise ValueError(f"Run must be extracted first, currently: {context.status.phase}")
        
        # Load use cases
        try:
            use_cases = load_use_cases(context.get_use_cases_file())
        except Exception as e:
            raise ValueError(f"Could not load use cases: {e}")
        
        # Check for existing analysis results to support resume capability
        results_file = context.data_dir / "results.json"
        existing_results = {}
        if results_file.exists():
            try:
                with open(results_file, 'r') as f:
                    existing_data = json.load(f)
                    # Create a map of use case number to existing results
                    for result in existing_data.get("use_case_results", []):
                        use_case_num = result.get("use_case_number")
                        if use_case_num and not result.get("error"):
                            existing_results[use_case_num] = result
                print(f"Found {len(existing_results)} previously analyzed use cases")
            except Exception as e:
                print(f"Warning: Could not load existing results: {e}")
        
        # Create queue of use cases to analyze (excluding already completed ones)
        pending_use_cases = []
        completed_results = []
        
        for i, use_case in enumerate(use_cases, 1):
            if i in existing_results:
                print(f"Skipping use case {i}/{len(use_cases)}: {use_case.name} (already analyzed)")
                completed_results.append(existing_results[i])
            else:
                pending_use_cases.append((i, use_case))
        
        print(f"Analyzing {len(pending_use_cases)} remaining use cases with {max_workers} workers")
        
        # Process use cases in parallel with semaphore to limit concurrency
        semaphore = asyncio.Semaphore(max_workers)
        
        async def analyze_with_semaphore(use_case_number: int, use_case: UseCase):
            async with semaphore:
                print(f"[Worker] Starting use case {use_case_number}/{len(use_cases)}: {use_case.name}")
                result = await self.analyze_use_case(
                    run_id=run_id,
                    use_case_number=use_case_number,
                    use_case=use_case,
                    context=context
                )
                print(f"[Worker] Completed use case {use_case_number}: {result.get('use_case_name', 'Unknown')}")
                return result
        
        # Execute all pending analyses concurrently
        if pending_use_cases:
            tasks = [
                analyze_with_semaphore(use_case_number, use_case)
                for use_case_number, use_case in pending_use_cases
            ]
            
            # Wait for all tasks to complete
            new_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Handle any exceptions that occurred
            for i, result in enumerate(new_results):
                if isinstance(result, Exception):
                    use_case_number, use_case = pending_use_cases[i]
                    error_result = {
                        "use_case_number": use_case_number,
                        "use_case_name": use_case.name,
                        "error": f"Analysis failed: {str(result)}",
                        "code_executability": {
                            "is_executable": False,
                            "execution_result": f"Analysis error: {str(result)}",
                            "failure_reason": "Analysis process failed",
                            "failed_due_to_api_key_error": "ANTHROPIC_API_KEY" in str(result)
                        }
                    }
                    new_results[i] = error_result
            
            completed_results.extend(new_results)
        
        # Sort results by use case number to maintain order
        use_case_results = sorted(completed_results, key=lambda x: x.get("use_case_number", 0))
        
        # Calculate success metrics
        successful_cases = 0
        failed_cases = 0
        
        for result in use_case_results:
            if result.get("code_executability", {}).get("is_executable", False):
                successful_cases += 1
            else:
                failed_cases += 1
        
        # Calculate overall summary
        total_cases = len(use_cases)
        success_rate = (successful_cases / total_cases) if total_cases > 0 else 0.0
        pass_fail_status = "PASS" if success_rate >= 0.5 else "FAIL"
        
        overall_summary = OverallSummary(
            pass_fail_status=pass_fail_status,
            success_rate=success_rate,
            total_use_cases=total_cases,
            successful_cases=successful_cases,
            failed_cases=failed_cases
        )
        
        # Analyze common failure patterns (simplified for now)
        common_failures = []
        if failed_cases > 0:
            # Group failures by common patterns
            error_patterns = {}
            for result in use_case_results:
                if not result.get("code_executability", {}).get("is_executable", False):
                    failure_reason = result.get("code_executability", {}).get("failure_reason", "Unknown error")
                    if "import" in failure_reason.lower() or "module" in failure_reason.lower():
                        pattern = "Import/Module Errors"
                    elif "api" in failure_reason.lower() or "key" in failure_reason.lower():
                        pattern = "API Key/Authentication Issues"  
                    elif "mock" in failure_reason.lower():
                        pattern = "Mocked Implementation"
                    else:
                        pattern = "Other Execution Errors"
                    
                    if pattern not in error_patterns:
                        error_patterns[pattern] = []
                    error_patterns[pattern].append(failure_reason)
            
            for pattern, examples in error_patterns.items():
                common_failures.append(CommonFailurePattern(
                    pattern=pattern,
                    frequency=len(examples),
                    examples=examples[:3],  # Keep top 3 examples
                    impact=f"Affects {len(examples)}/{total_cases} use cases"
                ))
        
        # Create final analysis result
        analysis_result = {
            "run_id": run_id,
            "repository_url": context.config.repo_url,
            "analysis_timestamp": overall_summary.analyzed_at.isoformat(),
            "overall_summary": overall_summary.model_dump(),
            "common_failures": [cf.model_dump() for cf in common_failures],
            "framework_insights": [],  # TODO: Implement framework-specific insights
            "use_case_results": use_case_results
        }
        
        # Save results
        results_file = context.data_dir / "results.json"
        with open(results_file, 'w') as f:
            json.dump(analysis_result, f, indent=2, default=str)
        
        # Update run context
        context.mark_analysis_completed()
        
        return analysis_result