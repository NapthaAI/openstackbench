"""Claude Code analyzer for StackBench implementation analysis."""

import asyncio
import json
import os
from pathlib import Path
from typing import Dict, List, Optional

from claude_code_sdk import ClaudeSDKClient, ClaudeCodeOptions

from ..config import get_config, find_env_file
from ..core.run_context import RunContext
from ..extractors.models import UseCase
from ..extractors.extractor import load_use_cases
from .models import UseCaseAnalysisResult

class ClaudeAnalyzer:
    """Claude Code-powered analyzer for use case implementations."""
    
    def __init__(self, config: Optional[Dict] = None, verbose: bool = False):
        self.config = get_config()
        self.verbose = verbose
        if config:
            # Override config values if provided
            for key, value in config.items():
                if hasattr(self.config, key):
                    setattr(self.config, key, value)
    
    def messages_to_dict(self, messages) -> List[Dict]:
        """Convert Claude Code messages to dictionary format for JSON serialization."""
        from dataclasses import asdict
        
        result = []
        for i, msg in enumerate(messages):
            try:
                # Use dataclass conversion if available
                if hasattr(msg, '__dataclass_fields__'):
                    msg_dict = asdict(msg)
                else:
                    # Fallback to manual conversion
                    msg_dict = {}
                    for attr in dir(msg):
                        if not attr.startswith('_') and not callable(getattr(msg, attr)):
                            try:
                                value = getattr(msg, attr)
                                # Convert non-serializable objects to strings
                                if isinstance(value, (str, int, float, bool, type(None))):
                                    msg_dict[attr] = value
                                elif isinstance(value, (list, dict)):
                                    msg_dict[attr] = value
                                else:
                                    msg_dict[attr] = str(value)
                            except Exception:
                                continue
                
                # Determine role based on message type
                msg_type = type(msg).__name__
                if 'SystemMessage' in msg_type:
                    msg_dict['role'] = 'system'
                elif 'AssistantMessage' in msg_type:
                    msg_dict['role'] = 'assistant'
                elif 'UserMessage' in msg_type:
                    msg_dict['role'] = 'user'
                else:
                    msg_dict['role'] = 'unknown'
                
                # Add message index and type info
                msg_dict['message_index'] = i
                msg_dict['message_type'] = msg_type
                
                result.append(msg_dict)
                
            except Exception as e:
                # Fallback for messages that can't be serialized
                result.append({
                    "message_index": i,
                    "role": "error",
                    "message_type": str(type(msg)),
                    "error": f"Could not serialize message: {str(e)}",
                })
        
        return result
    
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
        
        # Get environment file path
        env_file = find_env_file()
        env_file_info = f"Environment file: `{env_file}`" if env_file else "No environment file found"
        
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
**{env_file_info}**

## Analysis Process

### Step 1: Read Main Implementation File ONLY
**CRITICAL:** Focus ONLY on the main implementation file: `{relative_target_file}`
- Do NOT read or analyze other files in the repository
- Do NOT explore the codebase beyond this single file
- Look for documentation tracking comments at the top
- Examine import statements and library usage
- Review implementation approach and patterns
- Check error handling and edge cases

### Step 2: Test Code Executability  
**IMPORTANT:** Test the implementation by running it exactly as written. Do NOT modify the code.
- You may set environment variables if needed (e.g., export API_KEY=test)
- You may install dependencies if needed
- Capture success output or error messages
- Assess code quality and functionality
- Focus ONLY on this single file's execution

### Step 3: Analyze Library Usage (Single File Only)
Determine if the implementation uses:
- Real library imports and methods
- Mock/fake implementations
- If mocked, try to understand why from the code comments and structure
- Base analysis ONLY on what's visible in the main implementation file

### Step 4: Documentation Analysis (Implementation File Only)
Since IDE agents don't have tool usage logs, analyze documentation usage from:
- "DOCUMENTATION CONSULTED" comments in the implementation
- Quality of implementation patterns used
- Evidence of following library conventions
- Base conclusions ONLY on the main implementation file content

## Required JSON Output
Save your analysis as a JSON file with this structure:

**IMPORTANT:** Use `"partial"` for is_executable when code runs but has limitations/issues.

```json
{UseCaseAnalysisResult.generate_json_example()}
```

**Save the analysis to:** `{target_file_path.parent.absolute()}/use_case_{use_case_number}_analysis.json`
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
        
        # Set up environment variables for Claude Code hooks - use absolute paths
        os.environ['CLAUDE_USE_CASE_ID'] = f"use_case_{use_case_number}"
        os.environ['CLAUDE_OUTPUT_DIR'] = str(use_case_dir.absolute())
        os.environ['CLAUDE_LOGS_DIR'] = str((context.data_dir / "logs").absolute())
        os.environ['CLAUDE_PROJECT_DIR'] = str(Path.cwd().absolute())  # Use current working directory as project root
        os.environ['CLAUDE_AGENT'] = 'stackbench_analyzer'
        
        # Ensure logs directory exists
        logs_dir = Path(os.environ['CLAUDE_LOGS_DIR'])
        logs_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"[Worker] Environment setup for use case {use_case_number}:")
        print(f"[Worker]   CLAUDE_USE_CASE_ID={os.environ['CLAUDE_USE_CASE_ID']}")
        print(f"[Worker]   CLAUDE_OUTPUT_DIR={os.environ['CLAUDE_OUTPUT_DIR']}")
        print(f"[Worker]   CLAUDE_LOGS_DIR={os.environ['CLAUDE_LOGS_DIR']}")
        print(f"[Worker]   CLAUDE_PROJECT_DIR={os.environ['CLAUDE_PROJECT_DIR']}")
        print(f"[Worker]   Logs directory exists: {logs_dir.exists()}")
        
        # Set up Claude Code client - run from StackBench project root so hooks are found
        options = ClaudeCodeOptions(
            system_prompt="You are a documentation analysis expert. Analyze implementations systematically and provide structured JSON output.",
            max_turns=self.config.analysis_max_turns,
            cwd=str(Path.cwd()),  # Run from StackBench project root where .claude directory is located
            allowed_tools=["Read", "Write", "Bash", "LS", "Grep"]
        )
        
        messages = []
        turn_count = 0
        
        try:
            print(f"[Worker] Starting analysis workflow for use case {use_case_number}")
            print(f"[Worker] Use case: {use_case.name}")
            print(f"[Worker] Output directory: {use_case_dir}")
            
            if self.verbose:
                print(f"[Worker] === ANALYSIS PROMPT ===")
                print(f"[Worker] Full prompt:\n{prompt}")
                print(f"[Worker] === END ANALYSIS PROMPT ===")
            else:
                # Show a preview of the prompt
                prompt_preview = prompt[:500] + "..." if len(prompt) > 500 else prompt
                print(f"[Worker] Prompt preview: {prompt_preview}")
            
            async with ClaudeSDKClient(options=options) as client:
                await client.query(prompt)
                
                # Collect and stream messages with turn tracking
                analysis_text = []
                async for message in client.receive_response():
                    messages.append(message)
                    turn_count += 1
                    print(f"[Worker] Use case {use_case_number}: Analysis turn {turn_count} completed")
                    
                    if self.verbose:
                        print(f"[Worker] Message: {message}")
                
                print(f"[Worker] Use case {use_case_number}: Analysis completed after {turn_count} turns")
                print(f"[Worker] Use case {use_case_number}: Collected {len(messages)} messages total")
                
                # Save analysis messages in the use case directory
                try:
                    messages_dict = self.messages_to_dict(messages)
                    analysis_messages_path = use_case_dir / f"use_case_{use_case_number}_analysis_messages.json"
                    with open(analysis_messages_path, 'w') as f:
                        json.dump(messages_dict, f, indent=2, default=str)
                    print(f"[Worker] Saved analysis messages to: {analysis_messages_path}")
                except Exception as e:
                    print(f"[Worker] Warning: Could not save analysis messages: {e}")
                
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
            use_cases = load_use_cases(context)
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
        
        # Update run context
        context.mark_analysis_completed()
        
        return use_case_results
    
    async def analyze_single_use_case(self, run_id: str, use_case_number: int) -> Dict:
        """Analyze a single specific use case."""
        
        try:
            context = RunContext.load(run_id)
        except Exception as e:
            raise ValueError(f"Could not load run context: {e}")
        
        # Validate run phase
        if context.status.phase not in ["extracted", "executed", "analyzed"]:
            raise ValueError(f"Run must be extracted first, currently: {context.status.phase}")
        
        # Load use cases
        try:
            use_cases = load_use_cases(context)
        except Exception as e:
            raise ValueError(f"Could not load use cases: {e}")
        
        # Validate use case number
        if use_case_number < 1 or use_case_number > len(use_cases):
            raise ValueError(f"Use case {use_case_number} not found. Available: 1-{len(use_cases)}")
        
        # Get the specific use case (1-based index)
        use_case = use_cases[use_case_number - 1]
        
        print(f"[Worker] Single use case analysis: {use_case_number}/{len(use_cases)}")
        
        # Analyze the single use case
        result = await self.analyze_use_case(
            run_id=run_id,
            use_case_number=use_case_number,
            use_case=use_case,
            context=context
        )
        
        print(f"[Worker] Single use case analysis completed: {result.get('use_case_name', 'Unknown')}")
        
        return result