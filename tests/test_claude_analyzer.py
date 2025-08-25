"""Tests for Claude analyzer functionality."""

import json
import shutil
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock, MagicMock

import pytest

from stackbench.analyzers.individual_analyzer import IndividualAnalyzer
from stackbench.analyzers.models import UseCaseAnalysisResult
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
def prepared_context_with_implementations(temp_data_dir, mock_use_cases):
    """Create a prepared run context with implementations."""
    context = RunContext.create(
        repo_url="https://github.com/user/test-repo",
        agent_type="cursor",
        base_data_dir=temp_data_dir
    )
    context.create_directories()
    context.mark_clone_completed()
    context.mark_extraction_completed(mock_use_cases)
    
    # Create solution files and mark use cases as executed
    for i in range(1, 4):
        use_case_dir = context.data_dir / f"use_case_{i}"
        use_case_dir.mkdir()
        solution_file = use_case_dir / "solution.py"
        solution_file.write_text(f"# Solution for use case {i}\nprint('Hello World {i}')")
        context.mark_use_case_executed(i, ExecutionMethod.IDE_MANUAL, solution_file)
    
    return context


@pytest.fixture
def mock_analysis_result():
    """Create mock analysis result."""
    return {
        "use_case_name": "Test Use Case",
        "use_case_number": 1,
        "code_executability": {
            "is_executable": True,
            "failure_reason": None,
            "syntax_errors": [],
            "runtime_errors": []
        },
        "underlying_library_usage": {
            "was_used": True,
            "was_mocked": False,
            "library_imports": ["requests"],
            "library_calls": ["requests.get()"],
            "mocking_analysis": {
                "initial_attempts": ["tried real API first"],
                "final_approach": "used real library"
            }
        },
        "quality_assessment": {
            "overall_score": 8,
            "code_structure": 8,
            "error_handling": 7,
            "best_practices": 8,
            "documentation_usage": 9
        },
        "documentation_tracking": {
            "files_consulted": ["README.md", "docs/api.md"],
            "implementation_notes": ["Used standard library approach"],
            "evidence_of_usage": "Code follows documented patterns"
        }
    }


class TestIndividualAnalyzer:
    """Test Claude analyzer initialization and basic functionality."""
    
    def test_analyzer_init_default(self):
        """Test analyzer initialization with defaults."""
        analyzer = IndividualAnalyzer()
        assert analyzer.verbose is False
        assert hasattr(analyzer, 'config')
    
    def test_analyzer_init_verbose(self):
        """Test analyzer initialization with verbose mode.""" 
        analyzer = IndividualAnalyzer(verbose=True)
        assert analyzer.verbose is True
    
    def test_analyzer_init_with_config(self):
        """Test analyzer initialization with custom config."""
        custom_config = {"analysis_max_turns": 20}
        analyzer = IndividualAnalyzer(config=custom_config, verbose=True)
        assert analyzer.verbose is True
        assert hasattr(analyzer, 'config')
    
    def test_messages_to_dict_empty(self):
        """Test message conversion with empty list."""
        analyzer = IndividualAnalyzer()
        result = analyzer.messages_to_dict([])
        assert result == []
    
    def test_messages_to_dict_with_mock_messages(self):
        """Test message conversion with mock messages."""
        analyzer = IndividualAnalyzer()
        
        # Create mock messages
        mock_msg1 = Mock()
        mock_msg1.__class__.__name__ = "UserMessage"
        mock_msg1.content = "Test message"
        mock_msg1.role = "user"
        
        mock_msg2 = Mock()
        mock_msg2.__class__.__name__ = "AssistantMessage"
        mock_msg2.content = "Test response"
        mock_msg2.role = "assistant"
        
        result = analyzer.messages_to_dict([mock_msg1, mock_msg2])
        
        assert len(result) == 2
        assert result[0]["role"] == "user"
        assert result[0]["message_index"] == 0
        assert result[1]["role"] == "assistant"  
        assert result[1]["message_index"] == 1


class TestSingleUseCaseAnalysis:
    """Test single use case analysis functionality."""
    
    @patch('stackbench.extractors.extractor.load_use_cases')
    @patch('stackbench.core.run_context.RunContext.load')
    def test_analyze_single_use_case_nonexistent(self, mock_load_context, mock_load_use_cases, 
                                                prepared_context_with_implementations, mock_use_cases):
        """Test analysis of nonexistent use case."""
        mock_load_context.return_value = prepared_context_with_implementations  
        mock_load_use_cases.return_value = mock_use_cases  # 3 use cases
        
        analyzer = IndividualAnalyzer()
        
        import asyncio
        with pytest.raises(ValueError, match="Use case 999 not found"):
            asyncio.run(analyzer.analyze_single_use_case("test-run-id", 999))
    
    
    def test_create_analysis_prompt(self, prepared_context_with_implementations, mock_use_cases):
        """Test creating analysis prompt."""
        analyzer = IndividualAnalyzer()
        use_case = mock_use_cases[0]
        target_file = prepared_context_with_implementations.data_dir / "use_case_1" / "solution.py"
        
        prompt = analyzer.create_analysis_prompt(
            use_case=use_case,
            use_case_number=1, 
            context=prepared_context_with_implementations,
            target_file_path=target_file
        )
        
        assert "Use Case 1" in prompt
        assert use_case.name in prompt
        assert use_case.elevator_pitch in prompt
        assert "solution.py" in prompt
        assert "JSON format" in prompt
        assert UseCaseAnalysisResult.generate_json_example() in prompt


class TestLoadUseCases:
    """Test use case loading functionality."""
    
    @patch('stackbench.extractors.extractor.load_use_cases')
    @patch('stackbench.core.run_context.RunContext.load')
    def test_analyze_run_invalid_phase(self, mock_load_context, mock_load_use_cases, temp_data_dir):
        """Test analyze_run with invalid phase."""
        # Create context in wrong phase
        context = RunContext.create("https://github.com/user/test-repo", base_data_dir=temp_data_dir)
        context.create_directories()
        # Don't mark as extracted (stays in created phase)
        
        mock_load_context.return_value = context
        
        analyzer = IndividualAnalyzer()
        
        import asyncio
        with pytest.raises(ValueError, match="Run must be extracted first"):
            asyncio.run(analyzer.analyze_run("test-run-id"))
    
    @patch('stackbench.extractors.extractor.load_use_cases')
    @patch('stackbench.core.run_context.RunContext.load')  
    def test_analyze_single_use_case_invalid_phase(self, mock_load_context, mock_load_use_cases, temp_data_dir):
        """Test analyze_single_use_case with invalid phase."""
        # Create context in wrong phase
        context = RunContext.create("https://github.com/user/test-repo", base_data_dir=temp_data_dir)
        context.create_directories()
        # Don't mark as extracted (stays in created phase)
        
        mock_load_context.return_value = context
        
        analyzer = IndividualAnalyzer()
        
        import asyncio
        with pytest.raises(ValueError, match="Run must be extracted first"):
            asyncio.run(analyzer.analyze_single_use_case("test-run-id", 1))
    
    def test_analyze_run_load_context_failure(self):
        """Test analyze_run when context loading fails."""
        analyzer = IndividualAnalyzer()
        
        import asyncio
        with pytest.raises(ValueError, match="Could not load run context"):
            asyncio.run(analyzer.analyze_run("nonexistent-run-id"))
    
    def test_analyze_single_use_case_load_context_failure(self):
        """Test analyze_single_use_case when context loading fails."""
        analyzer = IndividualAnalyzer()
        
        import asyncio
        with pytest.raises(ValueError, match="Could not load run context"):
            asyncio.run(analyzer.analyze_single_use_case("nonexistent-run-id", 1))


if __name__ == "__main__":
    pytest.main([__file__])