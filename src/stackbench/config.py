"""Configuration management for StackBench using Pydantic."""

from pathlib import Path
from typing import List, Optional

from pydantic import ConfigDict, Field, field_validator
from pydantic_settings import BaseSettings


class Config(BaseSettings):
    """Configuration class with hierarchical loading support via Pydantic."""
    
    # Core directories
    data_dir: Path = Field(default=Path("data"))
    
    # DSPy settings (essential for extraction)
    dspy_model: str = "gpt-4o-mini"
    dspy_cache: bool = True
    dspy_max_tokens: int = 10000
    
    # Extraction settings
    num_use_cases: int = 10
    use_case_max_workers: int = 4
    include_folders: List[str] = Field(default=[])
    
    # Agent settings
    default_agent: str = "cursor"
    env_file_path: str = ".env"  # Path to environment file relative to repository root
    
    # Claude Code analysis settings
    anthropic_api_key: Optional[str] = None
    claude_model: str = "claude-sonnet-4"
    analysis_max_turns: int = 30
    
    # Logging
    log_level: str = "INFO"
    
    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in valid_levels:
            raise ValueError(f"log_level must be one of {valid_levels}")
        return v.upper()
    
    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"  # Allow extra fields like API keys
    )


def get_config() -> Config:
    """Get the global configuration instance."""
    return Config()