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
            
            # Clean up non-documentation files to save space and focus on relevant content
            self.cleanup_non_documentation_files(context.repo_dir)
            
            # Mark clone as completed and save
            context.mark_clone_completed()
            
            return context
            
        except Exception as e:
            # Cleanup on failure
            if context.run_dir.exists():
                shutil.rmtree(context.run_dir)
            raise RuntimeError(f"Failed to clone repository {repo_url}: {e}")
    
    def cleanup_non_documentation_files(self, repo_dir: Path) -> None:
        """Remove all files except documentation and configuration files.
        
        Keeps only: .md, .mdx, .toml, .json, .yaml, .yml files
        Preserves: .git directory and its contents
        Removes: All other files and empty directories
        
        Args:
            repo_dir: Path to the cloned repository directory
        """
        allowed_extensions = {'.md', '.mdx', '.toml', '.json', '.yaml', '.yml'}
        preserved_dirs = {'.git'}
        
        # Walk the directory tree from bottom up to handle directory removal
        for root, dirs, files in os.walk(repo_dir, topdown=False):
            root_path = Path(root)
            
            # Skip .git directory and its contents
            if any(preserved_dir in root_path.parts for preserved_dir in preserved_dirs):
                continue
            
            # Remove files that don't match allowed extensions
            for file in files:
                file_path = root_path / file
                if file_path.suffix.lower() not in allowed_extensions:
                    try:
                        file_path.unlink()
                    except OSError:
                        # Skip files that can't be removed (permissions, etc.)
                        pass
            
            # Remove empty directories (but not the root repo directory)
            if root_path != repo_dir:
                try:
                    # Only remove if directory is empty
                    if not any(root_path.iterdir()):
                        root_path.rmdir()
                except OSError:
                    # Directory not empty or can't be removed
                    pass
    
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