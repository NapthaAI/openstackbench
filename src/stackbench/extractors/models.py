"""Pydantic models for use case extraction."""

from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class Document(BaseModel):
    """A documentation file with content and metadata."""
    
    file_path: Path
    content: str = Field(description="Full content of the document")
    truncated_content: str = Field(description="Content truncated to fit token limits")
    num_tokens: int = Field(description="Number of tokens in the content")


class UseCase(BaseModel):
    """A use case extracted from documentation for agent execution."""
    
    # Core Identity
    name: str = Field(description="Name of the use case")
    elevator_pitch: str = Field(description="One paragraph pitch of what this use case accomplishes")
    target_audience: str = Field(description="Who would use this (developers, beginners, etc.)")
    
    # Requirements & Stories  
    functional_requirements: List[str] = Field(description="What the implementation should do")
    user_stories: List[str] = Field(description="How users will interact with the solution")
    
    # Technical Design
    system_design: str = Field(description="High-level system design approach")
    architecture_pattern: str = Field(description="Architecture pattern to follow")
    
    # Meta Information
    complexity_level: str = Field(description="Beginner/Intermediate/Advanced")
    source_document: List[str] = Field(description="Source documentation files")
    real_world_scenario: str = Field(description="Real-world context for this use case")
    
    # Execution details (added for agent execution)
    target_file: str = Field(description="Relative path where solution should be created", default="solution.py")
    
    @field_validator("functional_requirements", "user_stories", "source_document")
    @classmethod
    def validate_non_empty_lists(cls, v):
        """Ensure required lists are not empty."""
        if not v:
            raise ValueError("List cannot be empty")
        return v


class ExtractionResult(BaseModel):
    """Result of the extraction process."""
    
    total_documents_processed: int
    documents_with_use_cases: int  
    total_use_cases_found: int
    final_use_cases: List[UseCase]
    processing_time_seconds: float
    errors: List[str] = Field(default_factory=list)