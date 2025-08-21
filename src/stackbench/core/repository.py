"""Repository management for cloning and organizing benchmark runs."""

import os
import shutil
from pathlib import Path
from typing import Optional, List

import git

from ..config import get_config
from .run_context import RunContext


class RepositoryManager:
    """Manages repository cloning and run organization."""
    
    def __init__(self, base_data_dir: Optional[Path] = None):
        config = get_config()
        self.base_data_dir = base_data_dir or config.data_dir
        self.base_data_dir.mkdir(parents=True, exist_ok=True)
    
    def clone_repository(
        self, 
        repo_url: str, 
        agent_type: Optional[str] = None,
        include_folders: Optional[List[str]] = None,
        num_use_cases: Optional[int] = None,
        branch: str = "main"
    ) -> RunContext:
        """Clone repository and set up run directory structure.
        
        Args:
            repo_url: Git repository URL to clone
            agent_type: Agent type to use for this run
            include_folders: Optional list of folders to focus on for extraction
            num_use_cases: Number of use cases to generate
            branch: Git branch to clone (default: main)
            
        Returns:
            RunContext with cloned repository and directory structure
        """
        # Create run context with configuration
        context = RunContext.create(
            repo_url=repo_url,
            agent_type=agent_type,
            include_folders=include_folders,
            num_use_cases=num_use_cases,
            base_data_dir=self.base_data_dir
        )
        context.create_directories()
        
        try:
            # Clone repository with specific branch
            git.Repo.clone_from(repo_url, context.repo_dir, branch=branch)
            
            # Mark clone as completed and save
            context.mark_clone_completed()
            
            return context
            
        except Exception as e:
            # Cleanup on failure
            if context.run_dir.exists():
                shutil.rmtree(context.run_dir)
            raise RuntimeError(f"Failed to clone repository {repo_url}: {e}")
    
    def find_markdown_files(self, context: RunContext, include_folders: Optional[List[str]] = None) -> List[Path]:
        """Find markdown files in the cloned repository.
        
        Args:
            context: Run context with repository path
            include_folders: Optional list of folders to search in (defaults to context config)
            
        Returns:
            List of markdown file paths
        """
        # Use include_folders from context config if not provided
        folders_to_search = include_folders or context.config.include_folders
        
        md_files = []
        
        for root, _, files in os.walk(context.repo_dir):
            # Filter directories if include_folders specified
            if folders_to_search:
                root_relative = Path(root).relative_to(context.repo_dir)
                if not any(folder in str(root_relative) for folder in folders_to_search):
                    continue
            
            for file in files:
                if file.endswith(('.md', '.mdx')):
                    md_files.append(Path(root) / file)
        
        return md_files
    
    def load_run_context(self, run_id: str) -> RunContext:
        """Load existing run context by ID."""
        return RunContext.load(run_id, self.base_data_dir)
    
    def list_runs(self) -> List[str]:
        """List all available run IDs."""
        if not self.base_data_dir.exists():
            return []
        
        runs = []
        for item in self.base_data_dir.iterdir():
            if item.is_dir() and (item / "run_context.json").exists():
                runs.append(item.name)
        
        return sorted(runs)
    
    def cleanup_run(self, run_id: str) -> None:
        """Remove a run directory and all its contents."""
        run_dir = self.base_data_dir / run_id
        if run_dir.exists():
            shutil.rmtree(run_dir)