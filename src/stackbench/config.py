"""Configuration management for StackBench using Pydantic."""

import os
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
    analysis_max_turns: int = 50
    analysis_max_workers: int = 3
    
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
        env_file_encoding="utf-8",
        extra="ignore"  # Allow extra fields like API keys
    )


def find_env_file() -> Optional[Path]:
    """Find the .env file, checking current directory and common locations."""
    # Check current working directory first
    cwd_env = Path.cwd() / ".env"
    if cwd_env.exists():
        return cwd_env
    
    # Check if we're in a project subdirectory, look up the tree
    current = Path.cwd()
    for parent in [current] + list(current.parents):
        env_file = parent / ".env"
        if env_file.exists():
            # Verify this looks like a project root (has pyproject.toml or setup.py)
            if (parent / "pyproject.toml").exists() or (parent / "setup.py").exists():
                return env_file
    
    return None


# Global config instance cache
_config_instance = None
_env_loaded = False


def get_config() -> Config:
    """Get the global configuration instance with proper environment file loading."""
    global _config_instance, _env_loaded
    
    # Load environment file only once
    if not _env_loaded:
        env_file = find_env_file()
        
        if env_file:
            print(f"Loading environment from: {env_file}")
            # Load using python-dotenv for better compatibility
            try:
                from dotenv import load_dotenv
                load_dotenv(env_file)
            except ImportError:
                # Fall back to manual loading if python-dotenv is not available
                try:
                    with open(env_file, 'r') as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith('#') and '=' in line:
                                key, value = line.split('=', 1)
                                os.environ[key.strip()] = value.strip()
                except Exception as e:
                    print(f"Warning: Could not load environment file {env_file}: {e}")
        else:
            print("No .env file found, using environment variables and defaults")
        
        _env_loaded = True
    
    # Create config instance only once
    if _config_instance is None:
        _config_instance = Config()
    
    return _config_instance