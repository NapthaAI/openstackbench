"""Run context for managing benchmark run state and configuration."""

import json
import uuid
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import List, Optional, Dict, Any, TYPE_CHECKING
from urllib.parse import urlparse

from pydantic import BaseModel, Field

from ..config import get_config

if TYPE_CHECKING:
    from ..extractors.models import UseCase


class ExecutionStatus(str, Enum):
    """Execution status for use cases."""
    NOT_EXECUTED = "not_executed"
    EXECUTED = "executed"
    FAILED = "failed"
    SKIPPED = "skipped"


class AnalysisStatus(str, Enum):
    """Analysis status for use cases."""
    NOT_ANALYZED = "not_analyzed"
    ANALYZED = "analyzed"
    FAILED = "failed"


class RunPhase(str, Enum):
    """Run phases for benchmark execution."""
    CREATED = "created"
    CLONED = "cloned"
    EXTRACTED = "extracted"
    EXECUTION = "execution"
    ANALYSIS_INDIVIDUAL = "analysis_individual"
    ANALYSIS_OVERALL = "analysis_overall"
    COMPLETED = "completed"


class ExecutionMethod(str, Enum):
    """Execution methods for use cases."""
    IDE_MANUAL = "ide_manual"
    CLI_AUTOMATED = "cli_automated"


class UseCaseState(BaseModel):
    """State tracking for an individual use case."""
    
    use_case_number: int
    name: str
    target_file: str = "solution.py"
    
    # Execution tracking
    execution_status: ExecutionStatus = ExecutionStatus.NOT_EXECUTED
    executed_at: Optional[datetime] = None
    execution_method: Optional[ExecutionMethod] = None
    execution_error: Optional[str] = None
    
    # Analysis tracking
    analysis_status: AnalysisStatus = AnalysisStatus.NOT_ANALYZED
    analyzed_at: Optional[datetime] = None
    analysis_error: Optional[str] = None
    
    # File tracking
    implementation_exists: bool = False
    analysis_exists: bool = False
    
    @property
    def is_executed(self) -> bool:
        """Check if use case has been executed successfully."""
        return self.execution_status == ExecutionStatus.EXECUTED
    
    @property
    def is_analyzed(self) -> bool:
        """Check if use case has been analyzed successfully."""
        return self.analysis_status == AnalysisStatus.ANALYZED
    
    @property
    def can_be_analyzed(self) -> bool:
        """Check if use case is ready for analysis (executed and has implementation file)."""
        return self.is_executed and self.implementation_exists


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
    """Enhanced status tracking for a benchmark run with use case level state."""
    
    # Phase tracking with new enhanced phases
    phase: RunPhase = RunPhase.CREATED
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    # Phase completion flags
    clone_completed: bool = False
    extraction_completed: bool = False
    execution_phase_completed: bool = False  # All use cases executed
    individual_analysis_completed: bool = False  # All use cases analyzed
    overall_analysis_completed: bool = False  # results.json + results.md generated
    
    # Use case state tracking
    use_cases: Dict[int, UseCaseState] = Field(default_factory=dict)
    total_use_cases: int = 0
    
    # Error tracking
    errors: List[str] = Field(default_factory=list)
    
    # Dynamic properties calculated from use_cases
    @property
    def executed_count(self) -> int:
        """Count of executed use cases."""
        return sum(1 for uc in self.use_cases.values() if uc.is_executed)
    
    @property
    def analyzed_count(self) -> int:
        """Count of analyzed use cases."""
        return sum(1 for uc in self.use_cases.values() if uc.is_analyzed)
    
    @property
    def execution_success_count(self) -> int:
        """Count of successfully executed use cases."""
        return sum(1 for uc in self.use_cases.values() if uc.execution_status == ExecutionStatus.EXECUTED)
    
    
    def update_phase(self, new_phase: RunPhase) -> None:
        """Update the current phase and timestamp."""
        self.phase = new_phase
        self.updated_at = datetime.now()
    
    def add_error(self, error: str) -> None:
        """Add an error to the tracking list."""
        self.errors.append(f"{datetime.now().isoformat()}: {error}")
    
    # State management methods
    def initialize_use_cases(self, use_cases: List["UseCase"]) -> None:
        """Initialize use case tracking from extracted use cases."""
        self.total_use_cases = len(use_cases)
        for i, use_case in enumerate(use_cases, 1):
            self.use_cases[i] = UseCaseState(
                use_case_number=i,
                name=use_case.name,
                target_file=use_case.target_file
            )
        self.updated_at = datetime.now()
    
    def mark_use_case_executed(
        self, 
        use_case_number: int, 
        method: ExecutionMethod, 
        implementation_file: Optional[Path] = None,
        error: Optional[str] = None
    ) -> None:
        """Mark a use case as executed."""
        if use_case_number not in self.use_cases:
            raise ValueError(f"Use case {use_case_number} not found")
        
        uc = self.use_cases[use_case_number]
        uc.execution_status = ExecutionStatus.EXECUTED if error is None else ExecutionStatus.FAILED
        uc.executed_at = datetime.now()
        uc.execution_method = method
        uc.execution_error = error
        uc.implementation_exists = implementation_file is not None and implementation_file.exists() if implementation_file else False
        self.updated_at = datetime.now()
    
    def mark_use_case_analyzed(
        self, 
        use_case_number: int, 
        analysis_file: Optional[Path] = None,
        error: Optional[str] = None
    ) -> None:
        """Mark a use case as analyzed."""
        if use_case_number not in self.use_cases:
            raise ValueError(f"Use case {use_case_number} not found")
        
        uc = self.use_cases[use_case_number]
        uc.analysis_status = AnalysisStatus.ANALYZED if error is None else AnalysisStatus.FAILED
        uc.analyzed_at = datetime.now()
        uc.analysis_error = error
        uc.analysis_exists = analysis_file is not None and analysis_file.exists() if analysis_file else False
        self.updated_at = datetime.now()
    
    def detect_completed_implementations(self, data_dir: Path) -> List[int]:
        """Detect completed implementations by checking for target files in use case directories."""
        completed = []
        for use_case_num in self.use_cases.keys():
            use_case_dir = data_dir / f"use_case_{use_case_num}"
            
            # Check if directory exists and has the target file
            if use_case_dir.exists():
                use_case = self.use_cases[use_case_num]
                target_file_path = use_case_dir / use_case.target_file
                
                # Check for the exact target file
                if target_file_path.exists():
                    self.use_cases[use_case_num].implementation_exists = True
                    completed.append(use_case_num)
        
        self.updated_at = datetime.now()
        return completed
    
    
    def get_ready_for_analysis(self) -> List[int]:
        """Get use cases that are ready to be analyzed (executed with implementation files)."""
        return [num for num, uc in self.use_cases.items() if uc.can_be_analyzed]
    
    def _is_ready_for_execution_phase(self) -> bool:
        """Check if ready to enter execution phase."""
        return self.extraction_completed and len(self.use_cases) > 0
    
    def _is_ready_for_individual_analysis(self) -> bool:
        """Check if ready to start individual analysis phase."""
        return self.execution_phase_completed and self.executed_count > 0
    
    def _is_ready_for_overall_analysis(self) -> bool:
        """Check if ready for overall analysis (results.json/md generation)."""
        return (self.individual_analysis_completed and 
                self.analyzed_count > 0)
    
    def _can_complete_execution_phase(self) -> bool:
        """Check if execution phase can be marked as complete."""
        # Execution phase is complete when all use cases have been executed
        return self.executed_count == self.total_use_cases
    
    def _can_complete_individual_analysis(self) -> bool:
        """Check if individual analysis phase can be marked as complete."""
        ready_count = len(self.get_ready_for_analysis())
        return ready_count > 0 and self.analyzed_count == ready_count
    
    def update_phase_automatically(self) -> RunPhase:
        """Update phase based on current state and return new phase.
        
        Phases represent completed work:
        - CLONED: cloning completed
        - EXTRACTED: extraction completed  
        - EXECUTION: execution completed
        - ANALYSIS_INDIVIDUAL: individual analysis completed
        - ANALYSIS_OVERALL: overall analysis completed
        - COMPLETED: everything done
        """
        if self.phase == RunPhase.CREATED and self.clone_completed:
            self.update_phase(RunPhase.CLONED)
        elif self.phase == RunPhase.CLONED and self.extraction_completed:
            self.update_phase(RunPhase.EXTRACTED)
        elif self.phase == RunPhase.EXTRACTED and self.execution_phase_completed:
            self.update_phase(RunPhase.EXECUTION)
        elif self.phase == RunPhase.EXECUTION and self.individual_analysis_completed:
            self.update_phase(RunPhase.ANALYSIS_INDIVIDUAL)
        elif self.phase == RunPhase.ANALYSIS_INDIVIDUAL and self.overall_analysis_completed:
            self.update_phase(RunPhase.ANALYSIS_OVERALL)
        elif self.phase == RunPhase.ANALYSIS_OVERALL:
            self.update_phase(RunPhase.COMPLETED)
        
        return self.phase


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
    
    def mark_clone_completed(self) -> None:
        """Mark the clone phase as completed."""
        self.status.clone_completed = True
        self.status.update_phase(RunPhase.CLONED)
        self.save()
    
    def mark_extraction_completed(self, use_cases: List["UseCase"]) -> None:
        """Mark the extraction phase as completed and initialize use case tracking."""
        self.status.extraction_completed = True
        self.status.initialize_use_cases(use_cases)
        self.status.update_phase_automatically()
        self.save()
    
    def mark_individual_analysis_completed(self) -> None:
        """Mark individual analysis phase as completed."""
        self.status.individual_analysis_completed = True
        # Ensure execution phase is also marked as completed since we can't analyze without execution
        if not self.status.execution_phase_completed:
            self.status.execution_phase_completed = True
        self.status.update_phase_automatically()
        self.save()
    
    def add_error(self, error: str) -> None:
        """Add an error to the run context."""
        self.status.add_error(error)
        self.save()
    
    def mark_use_case_executed(
        self, 
        use_case_number: int, 
        method: ExecutionMethod, 
        implementation_file: Optional[Path] = None,
        error: Optional[str] = None
    ) -> None:
        """Mark a use case as executed and save context."""
        self.status.mark_use_case_executed(use_case_number, method, implementation_file, error)
        self.save()
    
    def mark_use_case_analyzed(
        self, 
        use_case_number: int, 
        analysis_file: Optional[Path] = None,
        error: Optional[str] = None
    ) -> None:
        """Mark a use case as analyzed and save context."""
        self.status.mark_use_case_analyzed(use_case_number, analysis_file, error)
        self.save()
    
    def detect_and_update_manual_implementations(self) -> List[int]:
        """Simple detection and update for IDE manual implementations."""
        # Find use cases with implementation files
        completed = self.status.detect_completed_implementations(self.data_dir)
        
        newly_detected = []
        for use_case_num in completed:
            uc = self.status.use_cases[use_case_num]
            # Only update if not already marked as executed
            if uc.execution_status == ExecutionStatus.NOT_EXECUTED:
                uc.execution_status = ExecutionStatus.EXECUTED
                uc.execution_method = ExecutionMethod.IDE_MANUAL
                uc.executed_at = datetime.now()
                newly_detected.append(use_case_num)
        
        # Update execution phase completion status and phase if we detected new implementations
        if newly_detected:
            # Check if execution phase should be marked as completed
            if self.status._can_complete_execution_phase():
                self.status.execution_phase_completed = True
            
            self.status.update_phase_automatically()
            self.save()
        
        return newly_detected
    
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
            "executed_use_cases": self.status.executed_count,
            "success_rate": (
                self.status.execution_success_count / self.status.executed_count 
                if self.status.executed_count > 0 else 0
            ),
            "has_errors": len(self.status.errors) > 0
        }