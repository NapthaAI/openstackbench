"""Tests for manual execution detection and use case state management."""

import shutil
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from stackbench.core.run_context import RunContext, ExecutionMethod, ExecutionStatus
from stackbench.extractors.models import UseCase


@pytest.fixture
def temp_data_dir():
    """Create a temporary directory for test data."""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def mock_use_cases():
    """Create mock use cases for testing."""
    return [
        UseCase(
            name=f"Use Case {i}",
            elevator_pitch="Test use case",
            target_audience="developers",
            functional_requirements=["req1"],
            user_stories=["story1"],
            system_design="simple",
            architecture_pattern="MVC",
            complexity_level="beginner",
            source_document=["test.md"],
            real_world_scenario="testing"
        ) for i in range(1, 4)
    ]


@pytest.fixture
def prepared_context(temp_data_dir, mock_use_cases):
    """Create a prepared run context with use cases initialized."""
    context = RunContext.create(
        repo_url="https://github.com/user/test-repo",
        agent_type="cursor",
        base_data_dir=temp_data_dir
    )
    context.create_directories()
    context.mark_clone_completed()
    context.mark_extraction_completed(mock_use_cases)
    return context


class TestManualExecutionDetection:
    """Test manual execution detection functionality."""
    
    def test_detect_no_implementations(self, prepared_context):
        """Test detection when no implementations exist."""
        completed = prepared_context.status.detect_completed_implementations(prepared_context.data_dir)
        
        assert completed == []
        assert all(not uc.implementation_exists for uc in prepared_context.status.use_cases.values())
    
    def test_detect_single_implementation(self, prepared_context):
        """Test detection of a single implementation file."""
        # Create use case directory with solution file
        use_case_dir = prepared_context.data_dir / "use_case_1"
        use_case_dir.mkdir()
        (use_case_dir / "solution.py").touch()
        
        completed = prepared_context.status.detect_completed_implementations(prepared_context.data_dir)
        
        assert completed == [1]
        assert prepared_context.status.use_cases[1].implementation_exists is True
        assert prepared_context.status.use_cases[2].implementation_exists is False
        assert prepared_context.status.use_cases[3].implementation_exists is False
    
    def test_detect_multiple_implementations(self, prepared_context):
        """Test detection of multiple implementation files."""
        # Create multiple use case directories with solution files
        for i in [1, 3]:
            use_case_dir = prepared_context.data_dir / f"use_case_{i}"
            use_case_dir.mkdir()
            (use_case_dir / "solution.py").touch()
        
        completed = prepared_context.status.detect_completed_implementations(prepared_context.data_dir)
        
        assert sorted(completed) == [1, 3]
        assert prepared_context.status.use_cases[1].implementation_exists is True
        assert prepared_context.status.use_cases[2].implementation_exists is False
        assert prepared_context.status.use_cases[3].implementation_exists is True
    
    def test_detect_different_solution_file_extensions(self, prepared_context):
        """Test detection of solution files with different extensions."""
        # Create use case directories with different solution file types
        test_cases = [
            (1, "solution.py"),
            (2, "solution.js"),
            (3, "solution.md")
        ]
        
        for use_case_num, filename in test_cases:
            use_case_dir = prepared_context.data_dir / f"use_case_{use_case_num}"
            use_case_dir.mkdir()
            (use_case_dir / filename).touch()
        
        completed = prepared_context.status.detect_completed_implementations(prepared_context.data_dir)
        
        assert sorted(completed) == [1, 2, 3]
        assert all(prepared_context.status.use_cases[i].implementation_exists for i in [1, 2, 3])
    
    def test_detect_ignores_non_solution_files(self, prepared_context):
        """Test that detection ignores files that don't start with 'solution'."""
        use_case_dir = prepared_context.data_dir / "use_case_1"
        use_case_dir.mkdir()
        
        # Create non-solution files
        (use_case_dir / "README.md").touch()
        (use_case_dir / "implementation.py").touch()
        (use_case_dir / "test.py").touch()
        
        completed = prepared_context.status.detect_completed_implementations(prepared_context.data_dir)
        
        assert completed == []
        assert prepared_context.status.use_cases[1].implementation_exists is False
    
    def test_detect_empty_use_case_directory(self, prepared_context):
        """Test detection handles empty use case directories."""
        # Create empty use case directory
        use_case_dir = prepared_context.data_dir / "use_case_1"
        use_case_dir.mkdir()
        
        completed = prepared_context.status.detect_completed_implementations(prepared_context.data_dir)
        
        assert completed == []
        assert prepared_context.status.use_cases[1].implementation_exists is False
    
    def test_detect_updates_timestamp(self, prepared_context):
        """Test that detection updates the updated_at timestamp."""
        original_time = prepared_context.status.updated_at
        
        # Small delay to ensure timestamp difference
        import time
        time.sleep(0.001)
        
        prepared_context.status.detect_completed_implementations(prepared_context.data_dir)
        
        assert prepared_context.status.updated_at > original_time


class TestManualImplementationUpdate:
    """Test the full manual implementation detection and update process."""
    
    def test_detect_and_update_no_changes(self, prepared_context):
        """Test update when no new implementations are detected."""
        newly_detected = prepared_context.detect_and_update_manual_implementations()
        
        assert newly_detected == []
        assert all(
            uc.execution_status == ExecutionStatus.NOT_EXECUTED 
            for uc in prepared_context.status.use_cases.values()
        )
    
    def test_detect_and_update_new_implementations(self, prepared_context):
        """Test update when new implementations are detected."""
        # Create solution files
        for i in [1, 3]:
            use_case_dir = prepared_context.data_dir / f"use_case_{i}"
            use_case_dir.mkdir()
            (use_case_dir / "solution.py").touch()
        
        newly_detected = prepared_context.detect_and_update_manual_implementations()
        
        assert sorted(newly_detected) == [1, 3]
        
        # Check that use cases were marked as executed
        assert prepared_context.status.use_cases[1].execution_status == ExecutionStatus.EXECUTED
        assert prepared_context.status.use_cases[1].execution_method == ExecutionMethod.IDE_MANUAL
        assert prepared_context.status.use_cases[1].executed_at is not None
        
        assert prepared_context.status.use_cases[2].execution_status == ExecutionStatus.NOT_EXECUTED
        
        assert prepared_context.status.use_cases[3].execution_status == ExecutionStatus.EXECUTED
        assert prepared_context.status.use_cases[3].execution_method == ExecutionMethod.IDE_MANUAL
        assert prepared_context.status.use_cases[3].executed_at is not None
    
    def test_detect_and_update_already_executed(self, prepared_context):
        """Test update when use case was already marked as executed."""
        # Manually mark use case as executed
        prepared_context.status.mark_use_case_executed(1, ExecutionMethod.CLI_AUTOMATED)
        
        # Create solution file for the same use case
        use_case_dir = prepared_context.data_dir / "use_case_1"
        use_case_dir.mkdir()
        (use_case_dir / "solution.py").touch()
        
        newly_detected = prepared_context.detect_and_update_manual_implementations()
        
        # Should not be newly detected since it was already executed
        assert newly_detected == []
        
        # Should still be marked as executed but with original method
        assert prepared_context.status.use_cases[1].execution_status == ExecutionStatus.EXECUTED
        assert prepared_context.status.use_cases[1].execution_method == ExecutionMethod.CLI_AUTOMATED
    
    def test_detect_and_update_triggers_phase_progression(self, prepared_context):
        """Test that detecting new implementations triggers phase progression."""
        # Initial phase should be extracted
        assert prepared_context.status.phase.value == "extracted"
        
        # Create solution files for all use cases
        for i in [1, 2, 3]:
            use_case_dir = prepared_context.data_dir / f"use_case_{i}"
            use_case_dir.mkdir()
            (use_case_dir / "solution.py").touch()
        
        newly_detected = prepared_context.detect_and_update_manual_implementations()
        
        assert len(newly_detected) == 3
        # Phase should progress to execution when implementations are detected
        assert prepared_context.status.phase.value == "execution"
        
        # To progress further, execution phase needs to be completed
        # This would happen when all use cases are executed (which they are now)
        # But the automatic phase progression only moves to execution, not beyond
        # Individual analysis phase progression happens when mark_individual_analysis_completed is called
    
    def test_detect_and_update_saves_context(self, prepared_context):
        """Test that updates are persisted to disk."""
        # Create solution file
        use_case_dir = prepared_context.data_dir / "use_case_1"
        use_case_dir.mkdir()
        (use_case_dir / "solution.py").touch()
        
        # Capture original context file modification time
        context_file = prepared_context.run_dir / "run_context.json"
        original_mtime = context_file.stat().st_mtime if context_file.exists() else 0
        
        prepared_context.detect_and_update_manual_implementations()
        
        # Context should be saved to disk
        assert context_file.exists()
        assert context_file.stat().st_mtime > original_mtime
        
        # Verify we can reload the context with the changes
        reloaded_context = RunContext.load(prepared_context.run_id, prepared_context.run_dir.parent)
        assert reloaded_context.status.use_cases[1].execution_status == ExecutionStatus.EXECUTED
        assert reloaded_context.status.use_cases[1].execution_method == ExecutionMethod.IDE_MANUAL


class TestUseCaseStateManagement:
    """Test use case state management methods."""
    
    def test_mark_use_case_executed_success(self, prepared_context):
        """Test marking a use case as successfully executed."""
        solution_file = prepared_context.data_dir / "use_case_1" / "solution.py"
        solution_file.parent.mkdir()
        solution_file.touch()
        
        prepared_context.mark_use_case_executed(1, ExecutionMethod.IDE_MANUAL, solution_file)
        
        uc = prepared_context.status.use_cases[1]
        assert uc.execution_status == ExecutionStatus.EXECUTED
        assert uc.execution_method == ExecutionMethod.IDE_MANUAL
        assert uc.executed_at is not None
        assert uc.execution_error is None
        assert uc.implementation_exists is True
    
    def test_mark_use_case_executed_failure(self, prepared_context):
        """Test marking a use case execution as failed."""
        error_msg = "Execution failed due to syntax error"
        
        prepared_context.mark_use_case_executed(1, ExecutionMethod.CLI_AUTOMATED, error=error_msg)
        
        uc = prepared_context.status.use_cases[1]
        assert uc.execution_status == ExecutionStatus.FAILED
        assert uc.execution_method == ExecutionMethod.CLI_AUTOMATED
        assert uc.executed_at is not None
        assert uc.execution_error == error_msg
        assert uc.implementation_exists is False
    
    def test_mark_use_case_analyzed_success(self, prepared_context):
        """Test marking a use case as successfully analyzed."""
        analysis_file = prepared_context.data_dir / "use_case_1" / "analysis.json"
        analysis_file.parent.mkdir()
        analysis_file.touch()
        
        prepared_context.mark_use_case_analyzed(1, analysis_file)
        
        uc = prepared_context.status.use_cases[1]
        assert uc.analysis_status.value == "analyzed"
        assert uc.analyzed_at is not None
        assert uc.analysis_error is None
        assert uc.analysis_exists is True
    
    def test_mark_use_case_analyzed_failure(self, prepared_context):
        """Test marking a use case analysis as failed."""
        error_msg = "Analysis failed due to invalid code"
        
        prepared_context.mark_use_case_analyzed(1, error=error_msg)
        
        uc = prepared_context.status.use_cases[1]
        assert uc.analysis_status.value == "failed"
        assert uc.analyzed_at is not None
        assert uc.analysis_error == error_msg
        assert uc.analysis_exists is False
    
    def test_mark_nonexistent_use_case(self, prepared_context):
        """Test that marking nonexistent use case raises error."""
        with pytest.raises(ValueError, match="Use case 999 not found"):
            prepared_context.mark_use_case_executed(999, ExecutionMethod.IDE_MANUAL)
        
        with pytest.raises(ValueError, match="Use case 999 not found"):
            prepared_context.mark_use_case_analyzed(999)


class TestUseCaseStateProperties:
    """Test use case state property methods."""
    
    def test_is_executed_property(self, prepared_context):
        """Test the is_executed property."""
        uc = prepared_context.status.use_cases[1]
        
        # Initially not executed
        assert not uc.is_executed
        
        # Mark as executed
        prepared_context.mark_use_case_executed(1, ExecutionMethod.IDE_MANUAL)
        assert uc.is_executed
        
        # Mark as failed
        prepared_context.status.use_cases[1].execution_status = ExecutionStatus.FAILED
        assert not uc.is_executed
    
    def test_is_analyzed_property(self, prepared_context):
        """Test the is_analyzed property."""
        uc = prepared_context.status.use_cases[1]
        
        # Initially not analyzed
        assert not uc.is_analyzed
        
        # Mark as analyzed
        prepared_context.mark_use_case_analyzed(1)
        assert uc.is_analyzed
    
    def test_can_be_analyzed_property(self, prepared_context):
        """Test the can_be_analyzed property."""
        uc = prepared_context.status.use_cases[1]
        
        # Initially cannot be analyzed (not executed)
        assert not uc.can_be_analyzed
        
        # Mark as executed but no implementation file
        prepared_context.mark_use_case_executed(1, ExecutionMethod.IDE_MANUAL)
        assert not uc.can_be_analyzed  # Still false due to no implementation file
        
        # Add implementation file
        uc.implementation_exists = True
        assert uc.can_be_analyzed  # Now true
        
        # Mark as failed execution
        uc.execution_status = ExecutionStatus.FAILED
        assert not uc.can_be_analyzed  # False again due to failed execution


if __name__ == "__main__":
    pytest.main([__file__])