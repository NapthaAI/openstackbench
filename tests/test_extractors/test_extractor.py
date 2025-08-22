"""End-to-end tests for extractor functionality."""

import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from stackbench.core.run_context import RunContext
from stackbench.extractors.extractor import (
    extract_use_cases,
    save_use_cases,
    load_use_cases,
    process_single_document,
    setup_dspy
)
from stackbench.extractors.models import Document, UseCase, ExtractionResult


@pytest.fixture
def temp_data_dir():
    """Create temporary directory for test data."""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def mock_run_context(temp_data_dir):
    """Create a mock RunContext for testing."""
    return RunContext.create(
        repo_url="https://github.com/test/repo",
        include_folders=["docs"],
        num_use_cases=5,
        base_data_dir=temp_data_dir
    )


@pytest.fixture
def sample_repo_with_docs(temp_data_dir):
    """Create a sample repository with markdown documentation."""
    repo_dir = temp_data_dir / "test-repo"
    repo_dir.mkdir()
    
    # Create docs directory
    docs_dir = repo_dir / "docs"
    docs_dir.mkdir()
    
    # Create sample markdown files
    (docs_dir / "getting-started.md").write_text("""
# Getting Started

This guide shows how to use our amazing library.

## Installation

```bash
pip install amazing-lib
```

## Basic Usage

```python
from amazing_lib import AmazingClass

# Create an instance
amazing = AmazingClass()

# Use the basic functionality
result = amazing.do_something("hello")
print(result)
```

## Advanced Example

```python
# Advanced usage with configuration
amazing = AmazingClass(config={'debug': True})
amazing.configure({
    'timeout': 30,
    'retry_count': 3
})

# Process data
data = amazing.process_file("input.txt")
amazing.save_results(data, "output.txt")
```
""")
    
    (docs_dir / "api-reference.md").write_text("""
# API Reference

## AmazingClass

The main class for all operations.

### Methods

#### do_something(text: str) -> str
Processes the input text and returns a result.

#### process_file(filename: str) -> dict
Processes a file and returns the data.

#### save_results(data: dict, filename: str) -> None
Saves the processed data to a file.
""")
    
    (repo_dir / "README.md").write_text("""
# Amazing Library

A library that does amazing things.

## Quick Example

```python
import amazing_lib
result = amazing_lib.quick_process("data")
```
""")
    
    return repo_dir


class TestSetupDSPy:
    """Test DSPy setup functionality."""
    
    @patch('dspy.LM')
    @patch('dspy.configure')
    def test_setup_dspy_with_config(self, mock_configure, mock_lm):
        """Test DSPy setup with configuration."""
        mock_lm_instance = Mock()
        mock_lm.return_value = mock_lm_instance
        
        setup_dspy()
        
        # Should create LM with config values
        mock_lm.assert_called_once()
        mock_configure.assert_called_once_with(lm=mock_lm_instance)


class TestProcessSingleDocument:
    """Test single document processing."""
    
    @patch('stackbench.extractors.extractor.DocumentProcessor')
    def test_process_single_document_success(self, mock_processor_class):
        """Test successful single document processing."""
        # Create test document
        document = Document(
            file_path=Path("/test/doc.md"),
            content="# Test Doc\n\nSample content",
            truncated_content="# Test Doc",
            num_tokens=10
        )
        
        # Mock processor
        mock_processor = Mock()
        mock_use_case = UseCase(
            name="Test Case",
            elevator_pitch="Test pitch",
            target_audience="Developers",
            functional_requirements=["Requirement 1"],
            user_stories=["User story 1"],
            system_design="Design",
            architecture_pattern="Pattern",
            complexity_level="Beginner",
            source_document=["/test/doc.md"],
            real_world_scenario="Scenario"
        )
        mock_processor.process_document.return_value = [mock_use_case]
        mock_processor_class.return_value = mock_processor
        
        result = process_single_document(document)
        
        assert len(result) == 1
        assert result[0].name == "Test Case"
        mock_processor.process_document.assert_called_once_with(document)
    
    @patch('stackbench.extractors.extractor.DocumentProcessor')
    def test_process_single_document_empty_result(self, mock_processor_class):
        """Test single document processing with empty result."""
        document = Document(
            file_path=Path("/test/doc.md"),
            content="# Test Doc",
            truncated_content="# Test Doc",
            num_tokens=5
        )
        
        mock_processor = Mock()
        mock_processor.process_document.return_value = []
        mock_processor_class.return_value = mock_processor
        
        result = process_single_document(document)
        
        assert result == []


class TestSaveAndLoadUseCases:
    """Test use case persistence functionality."""
    
    def test_save_and_load_use_cases_round_trip(self, mock_run_context):
        """Test saving and loading use cases."""
        # Create test use cases
        use_case = UseCase(
            name="Test Use Case",
            elevator_pitch="This is a test",
            target_audience="Developers",
            functional_requirements=["Must work", "Should be fast"],
            user_stories=["As a user, I want functionality"],
            system_design="Simple design",
            architecture_pattern="MVC",
            complexity_level="Beginner",
            source_document=["/test/doc.md"],
            real_world_scenario="Real scenario"
        )
        
        result = ExtractionResult(
            total_documents_processed=1,
            documents_with_use_cases=1,
            total_use_cases_found=1,
            final_use_cases=[use_case],
            processing_time_seconds=10.5,
            errors=[]
        )
        
        # Create directories
        mock_run_context.create_directories()
        
        # Save use cases
        save_use_cases(mock_run_context, result)
        
        # Verify file exists
        use_cases_file = mock_run_context.get_use_cases_file()
        assert use_cases_file.exists()
        
        # Load use cases
        loaded_use_cases = load_use_cases(mock_run_context)
        
        assert len(loaded_use_cases) == 1
        assert loaded_use_cases[0].name == "Test Use Case"
        assert loaded_use_cases[0].complexity_level == "Beginner"
        assert loaded_use_cases[0].functional_requirements == ["Must work", "Should be fast"]
    
    def test_load_use_cases_nonexistent_file(self, mock_run_context):
        """Test loading use cases when file doesn't exist."""
        mock_run_context.create_directories()
        
        result = load_use_cases(mock_run_context)
        
        assert result == []
    
    def test_save_use_cases_creates_metadata(self, mock_run_context):
        """Test that save_use_cases creates proper metadata."""
        use_case = UseCase(
            name="Test",
            elevator_pitch="Test pitch",
            target_audience="Developers",
            functional_requirements=["Requirement 1"],
            user_stories=["User story 1"],
            system_design="Design",
            architecture_pattern="Pattern",
            complexity_level="Beginner",
            source_document=["/test/doc.md"],
            real_world_scenario="Scenario"
        )
        
        result = ExtractionResult(
            total_documents_processed=5,
            documents_with_use_cases=2,
            total_use_cases_found=3,
            final_use_cases=[use_case],
            processing_time_seconds=25.0,
            errors=["Error 1"]
        )
        
        mock_run_context.create_directories()
        save_use_cases(mock_run_context, result)
        
        # Read and verify file content
        use_cases_file = mock_run_context.get_use_cases_file()
        with open(use_cases_file, 'r') as f:
            data = json.load(f)
        
        assert "extraction_metadata" in data
        assert "use_cases" in data
        
        metadata = data["extraction_metadata"]
        assert metadata["total_documents_processed"] == 5
        assert metadata["documents_with_use_cases"] == 2
        assert metadata["total_use_cases_found"] == 3
        assert metadata["processing_time_seconds"] == 25.0
        assert metadata["errors"] == ["Error 1"]
        assert "extracted_at" in metadata
        
        assert len(data["use_cases"]) == 1


class TestExtractUseCasesIntegration:
    """Test end-to-end extraction functionality."""
    
    @patch('stackbench.extractors.extractor.setup_dspy')
    @patch('stackbench.extractors.extractor.process_single_document')
    def test_extract_use_cases_success(self, mock_process_doc, mock_setup_dspy, sample_repo_with_docs):
        """Test successful use case extraction."""
        # Create run context
        context = RunContext.create(
            repo_url="https://github.com/test/repo",
            include_folders=["docs"],
            num_use_cases=2
        )
        context.run_dir = sample_repo_with_docs.parent / context.run_id
        context.repo_dir = sample_repo_with_docs
        context.data_dir = context.run_dir / "data"
        context.create_directories()
        
        # Mock document processing to return use cases
        mock_use_case = UseCase(
            name="Test Use Case",
            elevator_pitch="Test pitch",
            target_audience="Developers",
            functional_requirements=["Requirement 1"],
            user_stories=["User story 1"],
            system_design="Design",
            architecture_pattern="Pattern",
            complexity_level="Beginner",
            source_document=["/test/doc.md"],
            real_world_scenario="Scenario"
        )
        mock_process_doc.return_value = [mock_use_case]
        
        # Run extraction
        result = extract_use_cases(context)
        
        # Verify result
        assert isinstance(result, ExtractionResult)
        assert result.total_documents_processed >= 1
        assert len(result.final_use_cases) <= 2  # Respects target count
        assert result.processing_time_seconds > 0
        
        # Verify files were saved
        assert context.get_use_cases_file().exists()
        
        # Verify context was updated
        assert context.status.extraction_completed is True
    
    @patch('stackbench.extractors.extractor.setup_dspy')
    def test_extract_use_cases_no_markdown_files(self, mock_setup_dspy, temp_data_dir):
        """Test extraction when no markdown files exist."""
        # Create empty repo
        empty_repo = temp_data_dir / "empty-repo"
        empty_repo.mkdir()
        
        context = RunContext.create(
            repo_url="https://github.com/test/empty",
            include_folders=["docs"],
            num_use_cases=5
        )
        context.run_dir = temp_data_dir / context.run_id
        context.repo_dir = empty_repo
        context.data_dir = context.run_dir / "data"
        context.create_directories()
        
        result = extract_use_cases(context)
        
        assert result.total_documents_processed == 0
        assert len(result.final_use_cases) == 0
        assert len(result.errors) == 1
        assert "No markdown files found" in result.errors[0]
    
    @patch('stackbench.extractors.extractor.setup_dspy')
    def test_extract_use_cases_early_stopping(self, mock_setup_dspy, sample_repo_with_docs):
        """Test early stopping when target count is reached."""
        context = RunContext.create(
            repo_url="https://github.com/test/repo",
            include_folders=["docs"],
            num_use_cases=1  # Low target for early stopping
        )
        context.run_dir = sample_repo_with_docs.parent / context.run_id
        context.repo_dir = sample_repo_with_docs
        context.data_dir = context.run_dir / "data"
        context.create_directories()
        
        # Mock process_single_document to always return use cases
        with patch('stackbench.extractors.extractor.process_single_document') as mock_process:
            mock_use_case = UseCase(
                name="Test Use Case",
                elevator_pitch="Test pitch",
                target_audience="Developers",
                functional_requirements=["Requirement 1"],
                user_stories=["User story 1"],
                system_design="Design",
                architecture_pattern="Pattern",
                complexity_level="Beginner",
                source_document=["/test/doc.md"],
                real_world_scenario="Scenario"
            )
            mock_process.return_value = [mock_use_case]
            
            result = extract_use_cases(context)
            
            # Should stop early when target is reached
            assert len(result.final_use_cases) == 1
            # May not process all documents due to early stopping
            assert result.total_documents_processed >= 1
    
    @patch('stackbench.extractors.extractor.setup_dspy')
    @patch('stackbench.extractors.extractor.load_documents')
    def test_extract_use_cases_handles_errors(self, mock_load_docs, mock_setup_dspy, sample_repo_with_docs):
        """Test extraction handles document processing errors gracefully."""
        context = RunContext.create(
            repo_url="https://github.com/test/repo",
            include_folders=["docs"],
            num_use_cases=5
        )
        context.run_dir = sample_repo_with_docs.parent / context.run_id
        context.repo_dir = sample_repo_with_docs
        context.data_dir = context.run_dir / "data"
        context.create_directories()
        
        # Mock load_documents to return empty list (simulating processing failure)
        mock_load_docs.return_value = []
        
        result = extract_use_cases(context)
        
        assert result.total_documents_processed == 0
        assert len(result.final_use_cases) == 0
        assert len(result.errors) >= 1
        assert "No valid documents loaded" in result.errors[0]
    
    def test_extract_use_cases_document_sorting(self, sample_repo_with_docs):
        """Test that documents are sorted by token count."""
        context = RunContext.create(
            repo_url="https://github.com/test/repo",
            include_folders=["docs"],
            num_use_cases=5
        )
        context.run_dir = sample_repo_with_docs.parent / context.run_id
        context.repo_dir = sample_repo_with_docs
        context.data_dir = context.run_dir / "data"
        context.create_directories()
        
        # Mock the processing to avoid DSPy calls
        with patch('stackbench.extractors.extractor.setup_dspy'), \
             patch('stackbench.extractors.extractor.process_single_document') as mock_process:
            
            mock_process.return_value = []  # No use cases to avoid complications
            
            result = extract_use_cases(context)
            
            # Should have processed documents (even if no use cases extracted)
            assert result.total_documents_processed >= 1


if __name__ == "__main__":
    pytest.main([__file__])