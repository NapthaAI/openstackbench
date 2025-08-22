"""Run context for managing benchmark run state and configuration."""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
from urllib.parse import urlparse

from pydantic import BaseModel, Field

from ..config import get_config


class RunConfig(BaseModel):
    """Configuration for a benchmark run."""
    
    # Repository settings
    repo_url: str
    include_folders: List[str] = Field(default_factory=list)
    
    # Extraction settings
    num_use_cases: int = Field(default_factory=lambda: get_config().num_use_cases)
    use_case_max_workers: int = Field(default_factory=lambda: get_config().use_case_max_workers)
    
    # Agent settings
    agent_type: str = Field(default_factory=lambda: get_config().default_agent)
    env_file_path: str = Field(default_factory=lambda: get_config().env_file_path)
    
    # DSPy settings
    dspy_model: str = Field(default_factory=lambda: get_config().dspy_model)
    dspy_max_tokens: int = Field(default_factory=lambda: get_config().dspy_max_tokens)
    dspy_cache: bool = Field(default_factory=lambda: get_config().dspy_cache)


class RunStatus(BaseModel):
    """Status tracking for a benchmark run."""
    
    phase: str = "created"  # created, cloned, extracted, executed, analyzed, completed, failed
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    # Phase completion tracking
    clone_completed: bool = False
    extraction_completed: bool = False
    execution_completed: bool = False
    analysis_completed: bool = False
    
    # Counts
    total_use_cases: int = 0
    executed_use_cases: int = 0
    successful_executions: int = 0
    failed_executions: int = 0
    
    # Error tracking
    errors: List[str] = Field(default_factory=list)
    
    def update_phase(self, new_phase: str) -> None:
        """Update the current phase and timestamp."""
        self.phase = new_phase
        self.updated_at = datetime.now()
    
    def add_error(self, error: str) -> None:
        """Add an error to the tracking list."""
        self.errors.append(f"{datetime.now().isoformat()}: {error}")


class RunContext(BaseModel):
    """Complete context for a benchmark run with UUID-based directory structure."""
    
    # Core identifiers
    run_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    repo_name: str
    
    # Directory structure
    run_dir: Path
    repo_dir: Path
    data_dir: Path
    
    # Configuration and status
    config: RunConfig
    status: RunStatus = Field(default_factory=RunStatus)
    
    # Additional metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @classmethod
    def create(
        cls, 
        repo_url: str, 
        agent_type: Optional[str] = None,
        include_folders: Optional[List[str]] = None,
        num_use_cases: Optional[int] = None,
        base_data_dir: Optional[Path] = None
    ) -> "RunContext":
        """Create a new run context with directory structure."""
        app_config = get_config()
        base_data_dir = base_data_dir or app_config.data_dir
        
        run_id = str(uuid.uuid4())
        repo_name = cls._extract_repo_name(repo_url)
        
        run_dir = base_data_dir / run_id
        repo_dir = run_dir / "repo"
        data_dir = run_dir / "data"
        
        # Create run configuration
        run_config = RunConfig(
            repo_url=repo_url,
            include_folders=include_folders or [],
            agent_type=agent_type or app_config.default_agent,
            num_use_cases=num_use_cases or app_config.num_use_cases
        )
        
        return cls(
            run_id=run_id,
            repo_name=repo_name,
            run_dir=run_dir,
            repo_dir=repo_dir,
            data_dir=data_dir,
            config=run_config
        )
    
    @staticmethod
    def _extract_repo_name(repo_url: str) -> str:
        """Extract repository name from URL."""
        parsed = urlparse(repo_url)
        path = parsed.path.strip('/')
        if path.endswith('.git'):
            path = path[:-4]
        return path.split('/')[-1] if '/' in path else path
    
    def create_directories(self) -> None:
        """Create the run directory structure."""
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.repo_dir.mkdir(exist_ok=True)
        self.data_dir.mkdir(exist_ok=True)
    
    def save(self) -> None:
        """Save the run context to persistent storage."""
        self.status.updated_at = datetime.now()
        
        config_file = self.run_dir / "run_context.json"
        with open(config_file, 'w') as f:
            # Convert to dict and handle Path serialization
            data = self.model_dump()
            data['run_dir'] = str(self.run_dir)
            data['repo_dir'] = str(self.repo_dir)
            data['data_dir'] = str(self.data_dir)
            json.dump(data, f, indent=2, default=str)
    
    @classmethod
    def load(cls, run_id: str, base_data_dir: Optional[Path] = None) -> "RunContext":
        """Load existing run context by ID."""
        app_config = get_config()
        base_data_dir = base_data_dir or app_config.data_dir
        
        run_dir = base_data_dir / run_id
        if not run_dir.exists():
            raise ValueError(f"Run {run_id} not found")
        
        config_file = run_dir / "run_context.json"
        if not config_file.exists():
            raise ValueError(f"Run context file not found for run {run_id}")
        
        with open(config_file, 'r') as f:
            data = json.load(f)
        
        # Convert path strings back to Path objects
        data['run_dir'] = Path(data['run_dir'])
        data['repo_dir'] = Path(data['repo_dir'])
        data['data_dir'] = Path(data['data_dir'])
        
        return cls(**data)
    
    def get_use_cases_file(self) -> Path:
        """Get path to use_cases.json file."""
        return self.data_dir / "use_cases.json"
    
    def get_results_file(self) -> Path:
        """Get path to results.json file."""
        return self.data_dir / "results.json"
    
    def get_analysis_file(self) -> Path:
        """Get path to analysis.json file."""
        return self.data_dir / "analysis.json"
    
    def get_use_case_dir(self, use_case_id: str) -> Path:
        """Get directory for a specific use case execution."""
        use_case_dir = self.data_dir / f"use_case_{use_case_id}"
        use_case_dir.mkdir(exist_ok=True)
        return use_case_dir
    
    def mark_clone_completed(self) -> None:
        """Mark the clone phase as completed."""
        self.status.clone_completed = True
        self.status.update_phase("cloned")
        self.save()
    
    def mark_extraction_completed(self, total_use_cases: int) -> None:
        """Mark the extraction phase as completed."""
        self.status.extraction_completed = True
        self.status.total_use_cases = total_use_cases
        self.status.update_phase("extracted")
        self.save()
    
    def mark_execution_completed(self, successful: int, failed: int) -> None:
        """Mark the execution phase as completed."""
        self.status.execution_completed = True
        self.status.executed_use_cases = successful + failed
        self.status.successful_executions = successful
        self.status.failed_executions = failed
        self.status.update_phase("executed")
        self.save()
    
    def mark_analysis_completed(self) -> None:
        """Mark the analysis phase as completed."""
        self.status.analysis_completed = True
        self.status.update_phase("analyzed")
        self.save()
    
    def add_error(self, error: str) -> None:
        """Add an error to the run context."""
        self.status.add_error(error)
        self.save()
    
    def is_manual_agent(self) -> bool:
        """Check if this run uses a manual (IDE) agent."""
        manual_agents = {"cursor", "vscode"}
        return self.config.agent_type.lower() in manual_agents
    
    def to_summary_dict(self) -> Dict[str, Any]:
        """Get a summary dictionary for display purposes."""
        return {
            "run_id": self.run_id,
            "repo_name": self.repo_name,
            "repo_url": self.config.repo_url,
            "agent_type": self.config.agent_type,
            "phase": self.status.phase,
            "created_at": self.status.created_at.isoformat(),
            "total_use_cases": self.status.total_use_cases,
            "executed_use_cases": self.status.executed_use_cases,
            "success_rate": (
                self.status.successful_executions / self.status.executed_use_cases 
                if self.status.executed_use_cases > 0 else 0
            ),
            "has_errors": len(self.status.errors) > 0
        }