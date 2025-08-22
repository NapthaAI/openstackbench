"""Abstract base class for StackBench agents."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List

from ..core.run_context import RunContext
from ..extractors.models import UseCase
from ..extractors.extractor import load_use_cases


class Agent(ABC):
    """Abstract base class for all StackBench agents."""
    
    @property
    @abstractmethod
    def agent_type(self) -> str:
        """Return 'ide' or 'cli' to distinguish agent categories."""
        pass
    
    @property
    @abstractmethod  
    def name(self) -> str:
        """Return agent name (e.g., 'cursor', 'openai', 'claude')."""
        pass
    
    @abstractmethod
    def format_prompt(self, run_id: str, use_case_number: int) -> str:
        """Format use case as executable prompt for this agent type."""
        pass
    
    def is_manual(self) -> bool:
        """Check if agent requires manual execution (IDE agents)."""
        return self.agent_type == "ide"
    
    def is_automated(self) -> bool:
        """Check if agent supports automated execution (CLI agents)."""
        return self.agent_type == "cli"
    
    def load_use_case(self, run_id: str, use_case_number: int) -> UseCase:
        """Load specific use case from run context."""
        context = RunContext.load(run_id)
        use_cases = load_use_cases(context)
        
        if not use_cases:
            raise ValueError(f"No use cases found for run {run_id}")
        
        if use_case_number < 1 or use_case_number > len(use_cases):
            raise ValueError(
                f"Use case number {use_case_number} is out of range. "
                f"Available: 1-{len(use_cases)}"
            )
        
        return use_cases[use_case_number - 1]  # Convert to 0-based index
    
    def get_target_directory(self, run_id: str, use_case_number: int) -> Path:
        """Get target directory for use case solution."""
        context = RunContext.load(run_id)
        use_case_dir = context.data_dir / f"use_case_{use_case_number}"
        use_case_dir.mkdir(exist_ok=True)
        return use_case_dir
    
    def get_run_context(self, run_id: str) -> RunContext:
        """Load run context for the given run ID."""
        return RunContext.load(run_id)