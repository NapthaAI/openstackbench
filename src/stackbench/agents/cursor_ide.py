"""Cursor IDE agent implementation."""

from pathlib import Path

from .base import Agent
from ..config import get_config, find_env_file


class CursorIDEAgent(Agent):
    """Agent for Cursor IDE manual execution."""
    
    @property
    def agent_type(self) -> str:
        return "ide"
    
    @property
    def name(self) -> str:
        return "cursor"
    
    def format_prompt(self, run_id: str, use_case_number: int) -> str:
        """Format use case for Cursor IDE execution."""
        use_case = self.load_use_case(run_id, use_case_number)
        context = self.get_run_context(run_id)
        target_dir = self.get_target_directory(run_id, use_case_number)
        
        # Use absolute paths for clarity
        absolute_target_dir = target_dir.resolve()
        absolute_repo_dir = context.repo_dir.resolve()
        
        # Get environment file path
        env_file = find_env_file()
        env_path_info = str(env_file) if env_file else ".env"
        
        prompt = f"""# {use_case.name}

## Use Case Details

**Elevator Pitch:** {use_case.elevator_pitch}

**Target Audience:** {use_case.target_audience}
**Complexity Level:** {use_case.complexity_level}
**Real-world Scenario:** {use_case.real_world_scenario}

### Functional Requirements
"""
        for i, req in enumerate(use_case.functional_requirements, 1):
            prompt += f"{i}. {req}\n"
        
        prompt += f"""
### User Stories
"""
        for i, story in enumerate(use_case.user_stories, 1):
            prompt += f"{i}. {story}\n"
        
        prompt += f"""
### System Design
{use_case.system_design}

### Architecture Pattern
{use_case.architecture_pattern}

## Instructions

Implement the use case described above.

**Documentation Location:** The repository documentation is located at `{absolute_repo_dir}`.

**Use Documentation for Help:** Please review and use the documentation in the repository to help you understand the library's APIs, patterns, and best practices.

**File Creation:** Create a single entry file called `{use_case.target_file}` (solution.py or solution.js depending on the library language).

**Target Directory:** Create the directory `{absolute_target_dir}` if it doesn't exist. All files that you decide to create should be placed in this directory.

**Documentation Tracking:** At the top of your solution file, include a comment block documenting which files you consulted:
```python
# DOCUMENTATION CONSULTED:
# - README.md: Overview of library structure and basic usage
# - docs/api/models.md: Model definitions and schema
# - examples/quickstart.py: Basic implementation patterns
# 
# IMPLEMENTATION NOTES:
# - Used real library imports and methods
# - Applied patterns from quickstart example
# - Handled edge cases based on API documentation
```

**Environment Setup:** There is a .env file at `{env_path_info}`. It contains important configuration variables, API keys, or settings needed for the library to work properly.
Always start your main script by loading the environment variables. For example:
```python
from dotenv import load_dotenv
load_dotenv(`{env_path_info}`)
```

### Implementation Requirements:
- Meet all functional requirements listed above
- Follow the specified architecture pattern  
- Be appropriate for the target audience complexity level
- Include proper error handling and documentation
- Use the repository's existing patterns and conventions
- Leverage the library's APIs and utilities where appropriate
- Include comments explaining your approach
- Consider edge cases and error scenarios

---
**Repository Path:** `{absolute_repo_dir}`
**Target Directory:** `{absolute_target_dir}`
**Main File:** `{absolute_target_dir}/{use_case.target_file}`
"""
        
        return prompt