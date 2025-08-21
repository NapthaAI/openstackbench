"""Tests for RepositoryManager and RunContext."""

import shutil
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from stackbench.core.repository import RepositoryManager
from stackbench.core.run_context import RunContext


@pytest.fixture
def temp_data_dir():
    """Create a temporary directory for test data."""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def repo_manager(temp_data_dir):
    """Create a RepositoryManager with temporary data directory."""
    return RepositoryManager(base_data_dir=temp_data_dir)


@pytest.fixture
def mock_git_repo():
    """Mock git.Repo.clone_from method."""
    with patch('stackbench.core.repository.git.Repo.clone_from') as mock:
        yield mock


class TestRunContext:
    """Test RunContext functionality."""
    
    def test_create_run_context(self, temp_data_dir):
        """Test creating a new run context."""
        context = RunContext.create(
            repo_url="https://github.com/user/test-repo",
            agent_type="cursor",
            include_folders=["docs"],
            num_use_cases=5,
            base_data_dir=temp_data_dir
        )
        
        assert context.repo_name == "test-repo"
        assert context.config.repo_url == "https://github.com/user/test-repo"
        assert context.config.agent_type == "cursor"
        assert context.config.include_folders == ["docs"]
        assert context.config.num_use_cases == 5
        assert context.status.phase == "created"
        
        # Check directory structure
        assert context.run_dir == temp_data_dir / context.run_id
        assert context.repo_dir == context.run_dir / "repo"
        assert context.data_dir == context.run_dir / "data"
    
    def test_extract_repo_name(self):
        """Test repository name extraction from various URLs."""
        test_cases = [
            ("https://github.com/user/repo", "repo"),
            ("https://github.com/user/repo.git", "repo"),
            ("git@github.com:user/repo.git", "repo"),
            ("https://gitlab.com/user/my-project", "my-project"),
        ]
        
        for url, expected_name in test_cases:
            name = RunContext._extract_repo_name(url)
            assert name == expected_name
    
    def test_create_directories(self, temp_data_dir):
        """Test directory creation."""
        context = RunContext.create("https://github.com/user/repo", base_data_dir=temp_data_dir)
        context.create_directories()
        
        assert context.run_dir.exists()
        assert context.repo_dir.exists()
        assert context.data_dir.exists()
    
    def test_save_and_load(self, temp_data_dir):
        """Test saving and loading run context."""
        # Create and save context
        original_context = RunContext.create(
            repo_url="https://github.com/user/repo",
            agent_type="cursor",
            include_folders=["docs"],
            base_data_dir=temp_data_dir
        )
        original_context.create_directories()
        original_context.mark_clone_completed()
        
        # Load context
        loaded_context = RunContext.load(original_context.run_id, temp_data_dir)
        
        assert loaded_context.run_id == original_context.run_id
        assert loaded_context.repo_name == original_context.repo_name
        assert loaded_context.config.repo_url == original_context.config.repo_url
        assert loaded_context.config.agent_type == original_context.config.agent_type
        assert loaded_context.config.include_folders == original_context.config.include_folders
        assert loaded_context.status.clone_completed is True
        assert loaded_context.status.phase == "cloned"
    
    def test_phase_transitions(self, temp_data_dir):
        """Test phase transition methods."""
        context = RunContext.create("https://github.com/user/repo", base_data_dir=temp_data_dir)
        context.create_directories()
        
        # Initial state
        assert context.status.phase == "created"
        assert not context.status.clone_completed
        
        # Mark clone completed
        context.mark_clone_completed()
        assert context.status.phase == "cloned"
        assert context.status.clone_completed
        
        # Mark extraction completed
        context.mark_extraction_completed(total_use_cases=10)
        assert context.status.phase == "extracted"
        assert context.status.extraction_completed
        assert context.status.total_use_cases == 10
        
        # Mark execution completed
        context.mark_execution_completed(successful=8, failed=2)
        assert context.status.phase == "executed"
        assert context.status.execution_completed
        assert context.status.successful_executions == 8
        assert context.status.failed_executions == 2
        assert context.status.executed_use_cases == 10
        
        # Mark analysis completed
        context.mark_analysis_completed()
        assert context.status.phase == "analyzed"
        assert context.status.analysis_completed
    
    def test_error_tracking(self, temp_data_dir):
        """Test error tracking functionality."""
        context = RunContext.create("https://github.com/user/repo", base_data_dir=temp_data_dir)
        context.create_directories()
        
        # Add errors
        context.add_error("Test error 1")
        context.add_error("Test error 2")
        
        assert len(context.status.errors) == 2
        assert "Test error 1" in context.status.errors[0]
        assert "Test error 2" in context.status.errors[1]
    
    def test_helper_methods(self, temp_data_dir):
        """Test helper methods for file paths."""
        context = RunContext.create("https://github.com/user/repo", base_data_dir=temp_data_dir)
        context.create_directories()
        
        # Test file path helpers
        assert context.get_use_cases_file() == context.data_dir / "use_cases.json"
        assert context.get_results_file() == context.data_dir / "results.json"
        assert context.get_analysis_file() == context.data_dir / "analysis.json"
        
        # Test use case directory creation
        use_case_dir = context.get_use_case_dir("1")
        assert use_case_dir == context.data_dir / "use_case_1"
        assert use_case_dir.exists()
    
    def test_manual_agent_detection(self, temp_data_dir):
        """Test manual agent detection."""
        cursor_context = RunContext.create(
            "https://github.com/user/repo", 
            agent_type="cursor",
            base_data_dir=temp_data_dir
        )
        assert cursor_context.is_manual_agent() is True
        
        openai_context = RunContext.create(
            "https://github.com/user/repo", 
            agent_type="openai",
            base_data_dir=temp_data_dir
        )
        assert openai_context.is_manual_agent() is False
    
    def test_summary_dict(self, temp_data_dir):
        """Test summary dictionary generation."""
        context = RunContext.create("https://github.com/user/repo", base_data_dir=temp_data_dir)
        context.create_directories()
        context.mark_extraction_completed(10)
        context.mark_execution_completed(8, 2)
        
        summary = context.to_summary_dict()
        
        assert summary["repo_name"] == "repo"
        assert summary["phase"] == "executed"
        assert summary["total_use_cases"] == 10
        assert summary["executed_use_cases"] == 10
        assert summary["success_rate"] == 0.8
        assert summary["has_errors"] is False


class TestRepositoryManager:
    """Test RepositoryManager functionality."""
    
    def test_init(self, temp_data_dir):
        """Test RepositoryManager initialization."""
        manager = RepositoryManager(base_data_dir=temp_data_dir)
        assert manager.base_data_dir == temp_data_dir
        assert temp_data_dir.exists()
    
    def test_clone_repository(self, repo_manager, mock_git_repo, temp_data_dir):
        """Test repository cloning."""
        # Mock successful clone
        mock_git_repo.return_value = Mock()
        
        context = repo_manager.clone_repository(
            repo_url="https://github.com/user/test-repo",
            agent_type="cursor",
            include_folders=["docs"],
            num_use_cases=5
        )
        
        # Check git clone was called
        mock_git_repo.assert_called_once_with(
            "https://github.com/user/test-repo", 
            context.repo_dir
        )
        
        # Check context properties
        assert context.repo_name == "test-repo"
        assert context.config.agent_type == "cursor"
        assert context.config.include_folders == ["docs"]
        assert context.config.num_use_cases == 5
        assert context.status.phase == "cloned"
        assert context.status.clone_completed is True
        
        # Check directories exist
        assert context.run_dir.exists()
        assert context.repo_dir.exists()
        assert context.data_dir.exists()
        
        # Check run context file was saved
        assert (context.run_dir / "run_context.json").exists()
    
    def test_clone_repository_failure(self, repo_manager, mock_git_repo):
        """Test repository cloning failure and cleanup."""
        # Mock clone failure
        mock_git_repo.side_effect = Exception("Clone failed")
        
        with pytest.raises(RuntimeError, match="Failed to clone repository"):
            repo_manager.clone_repository("https://github.com/user/test-repo")
        
        # Check no directories were left behind
        assert len(list(repo_manager.base_data_dir.iterdir())) == 0
    
    def test_find_markdown_files(self, repo_manager, mock_git_repo, temp_data_dir):
        """Test finding markdown files."""
        # Create mock repository structure
        mock_git_repo.return_value = Mock()
        context = repo_manager.clone_repository("https://github.com/user/test-repo")
        
        # Create test markdown files
        (context.repo_dir / "README.md").touch()
        (context.repo_dir / "docs").mkdir()
        (context.repo_dir / "docs" / "guide.md").touch()
        (context.repo_dir / "docs" / "api.mdx").touch()
        (context.repo_dir / "src").mkdir()
        (context.repo_dir / "src" / "notes.md").touch()
        
        # Test finding all markdown files
        all_files = repo_manager.find_markdown_files(context)
        assert len(all_files) == 4
        
        # Test with include_folders filter
        docs_files = repo_manager.find_markdown_files(context, include_folders=["docs"])
        assert len(docs_files) == 2
        
        # Test using context config include_folders
        context.config.include_folders = ["docs"]
        context_filtered = repo_manager.find_markdown_files(context)
        assert len(context_filtered) == 2
    
    def test_load_run_context(self, repo_manager, mock_git_repo):
        """Test loading existing run context."""
        # Create a run
        mock_git_repo.return_value = Mock()
        original_context = repo_manager.clone_repository("https://github.com/user/test-repo")
        run_id = original_context.run_id
        
        # Load the run
        loaded_context = repo_manager.load_run_context(run_id)
        
        assert loaded_context.run_id == run_id
        assert loaded_context.repo_name == "test-repo"
        assert loaded_context.config.repo_url == "https://github.com/user/test-repo"
    
    def test_load_nonexistent_run(self, repo_manager):
        """Test loading nonexistent run context."""
        with pytest.raises(ValueError, match="Run nonexistent not found"):
            repo_manager.load_run_context("nonexistent")
    
    def test_list_runs(self, repo_manager, mock_git_repo):
        """Test listing available runs."""
        # Initially no runs
        assert repo_manager.list_runs() == []
        
        # Create some runs
        mock_git_repo.return_value = Mock()
        context1 = repo_manager.clone_repository("https://github.com/user/repo1")
        context2 = repo_manager.clone_repository("https://github.com/user/repo2")
        
        # List runs
        runs = repo_manager.list_runs()
        assert len(runs) == 2
        assert context1.run_id in runs
        assert context2.run_id in runs
        assert runs == sorted(runs)  # Should be sorted
    
    def test_cleanup_run(self, repo_manager, mock_git_repo):
        """Test cleaning up a run."""
        # Create a run
        mock_git_repo.return_value = Mock()
        context = repo_manager.clone_repository("https://github.com/user/test-repo")
        run_id = context.run_id
        
        # Verify run exists
        assert context.run_dir.exists()
        assert run_id in repo_manager.list_runs()
        
        # Cleanup run
        repo_manager.cleanup_run(run_id)
        
        # Verify run is gone
        assert not context.run_dir.exists()
        assert run_id not in repo_manager.list_runs()
    
    def test_cleanup_nonexistent_run(self, repo_manager):
        """Test cleaning up nonexistent run (should not raise error)."""
        # Should not raise an error
        repo_manager.cleanup_run("nonexistent")


if __name__ == "__main__":
    pytest.main([__file__])