"""Tests for extractor Pydantic models."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from stackbench.extractors.models import Document, UseCase, ExtractionResult


class TestDocument:
    """Test Document model validation and functionality."""
    
    def test_document_creation_valid(self):
        """Test creating a valid Document."""
        doc = Document(
            file_path=Path("/test/file.md"),
            content="# Test Document\n\nContent here.",
            truncated_content="# Test Document",
            num_tokens=50
        )
        
        assert doc.file_path == Path("/test/file.md")
        assert doc.content == "# Test Document\n\nContent here."
        assert doc.truncated_content == "# Test Document"
        assert doc.num_tokens == 50
    
    def test_document_path_conversion(self):
        """Test that string paths are converted to Path objects."""
        doc = Document(
            file_path="/test/file.md",  # String path
            content="Content",
            truncated_content="Content",
            num_tokens=10
        )
        
        assert isinstance(doc.file_path, Path)
        assert doc.file_path == Path("/test/file.md")
    
    def test_document_missing_required_fields(self):
        """Test Document creation with missing required fields."""
        with pytest.raises(ValidationError) as excinfo:
            Document(
                file_path=Path("/test/file.md")
                # Missing content, truncated_content, num_tokens
            )
        
        error = excinfo.value
        assert "content" in str(error)
        assert "truncated_content" in str(error)
        assert "num_tokens" in str(error)
    
    def test_document_invalid_types(self):
        """Test Document creation with invalid field types."""
        with pytest.raises(ValidationError):
            Document(
                file_path="/test/file.md",
                content="Content",
                truncated_content="Content",
                num_tokens="not_a_number"  # Should be int
            )


class TestUseCase:
    """Test UseCase model validation and functionality."""
    
    def test_usecase_creation_complete(self):
        """Test creating a complete UseCase."""
        use_case = UseCase(
            name="Test Use Case",
            elevator_pitch="This is a test use case for demonstration.",
            target_audience="Developers",
            functional_requirements=["Requirement 1", "Requirement 2"],
            user_stories=["As a user, I want to test"],
            system_design="Simple system design",
            architecture_pattern="MVC",
            complexity_level="Beginner",
            source_document=["/test/doc.md"],
            real_world_scenario="Testing scenario",
            target_file="test_solution.py"
        )
        
        assert use_case.name == "Test Use Case"
        assert use_case.elevator_pitch == "This is a test use case for demonstration."
        assert use_case.target_audience == "Developers"
        assert len(use_case.functional_requirements) == 2
        assert len(use_case.user_stories) == 1
        assert use_case.system_design == "Simple system design"
        assert use_case.architecture_pattern == "MVC"
        assert use_case.complexity_level == "Beginner"
        assert use_case.source_document == ["/test/doc.md"]
        assert use_case.real_world_scenario == "Testing scenario"
        assert use_case.target_file == "test_solution.py"
    
    def test_usecase_default_target_file(self):
        """Test UseCase with default target_file."""
        use_case = UseCase(
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
            # target_file not specified - should use default
        )
        
        assert use_case.target_file == "solution.py"
    
    def test_usecase_missing_core_identity(self):
        """Test UseCase creation missing core identity fields."""
        with pytest.raises(ValidationError) as excinfo:
            UseCase(
                # Missing name, elevator_pitch, target_audience
                functional_requirements=["Requirement 1"],
                user_stories=["User story 1"],
                system_design="Design",
                architecture_pattern="Pattern",
                complexity_level="Beginner",
                source_document=["/test/doc.md"],
                real_world_scenario="Scenario"
            )
        
        error = excinfo.value
        assert "name" in str(error)
        assert "elevator_pitch" in str(error)
        assert "target_audience" in str(error)
    
    def test_usecase_missing_requirements(self):
        """Test UseCase creation missing requirements fields."""
        with pytest.raises(ValidationError) as excinfo:
            UseCase(
                name="Test",
                elevator_pitch="Test pitch",
                target_audience="Developers",
                # Missing functional_requirements, user_stories
                system_design="Design",
                architecture_pattern="Pattern",
                complexity_level="Beginner",
                source_document=["/test/doc.md"],
                real_world_scenario="Scenario"
            )
        
        error = excinfo.value
        assert "functional_requirements" in str(error)
        assert "user_stories" in str(error)
    
    def test_usecase_missing_technical_design(self):
        """Test UseCase creation missing technical design fields."""
        with pytest.raises(ValidationError) as excinfo:
            UseCase(
                name="Test",
                elevator_pitch="Test pitch",
                target_audience="Developers",
                functional_requirements=["Requirement 1"],
                user_stories=["User story 1"],
                # Missing system_design, architecture_pattern
                complexity_level="Beginner",
                source_document=["/test/doc.md"],
                real_world_scenario="Scenario"
            )
        
        error = excinfo.value
        assert "system_design" in str(error)
        assert "architecture_pattern" in str(error)
    
    def test_usecase_missing_meta_information(self):
        """Test UseCase creation missing meta information fields."""
        with pytest.raises(ValidationError) as excinfo:
            UseCase(
                name="Test",
                elevator_pitch="Test pitch",
                target_audience="Developers",
                functional_requirements=["Requirement 1"],
                user_stories=["User story 1"],
                system_design="Design",
                architecture_pattern="Pattern",
                # Missing complexity_level, source_document, real_world_scenario
            )
        
        error = excinfo.value
        assert "complexity_level" in str(error)
        assert "source_document" in str(error)
        assert "real_world_scenario" in str(error)
    
    def test_usecase_empty_lists_invalid(self):
        """Test UseCase creation with empty required lists."""
        with pytest.raises(ValidationError):
            UseCase(
                name="Test",
                elevator_pitch="Test pitch",
                target_audience="Developers",
                functional_requirements=[],  # Empty list should be invalid
                user_stories=["User story 1"],
                system_design="Design",
                architecture_pattern="Pattern",
                complexity_level="Beginner",
                source_document=["/test/doc.md"],
                real_world_scenario="Scenario"
            )
    
    def test_usecase_complexity_levels(self):
        """Test UseCase with different complexity levels."""
        valid_levels = ["Beginner", "Intermediate", "Advanced"]
        
        for level in valid_levels:
            use_case = UseCase(
                name="Test",
                elevator_pitch="Test pitch",
                target_audience="Developers",
                functional_requirements=["Requirement 1"],
                user_stories=["User story 1"],
                system_design="Design",
                architecture_pattern="Pattern",
                complexity_level=level,
                source_document=["/test/doc.md"],
                real_world_scenario="Scenario"
            )
            assert use_case.complexity_level == level
    
    def test_usecase_multiple_source_documents(self):
        """Test UseCase with multiple source documents."""
        use_case = UseCase(
            name="Test",
            elevator_pitch="Test pitch",
            target_audience="Developers",
            functional_requirements=["Requirement 1"],
            user_stories=["User story 1"],
            system_design="Design",
            architecture_pattern="Pattern",
            complexity_level="Beginner",
            source_document=["/test/doc1.md", "/test/doc2.md", "/test/doc3.md"],
            real_world_scenario="Scenario"
        )
        
        assert len(use_case.source_document) == 3
        assert "/test/doc1.md" in use_case.source_document
        assert "/test/doc2.md" in use_case.source_document
        assert "/test/doc3.md" in use_case.source_document


class TestExtractionResult:
    """Test ExtractionResult model validation and functionality."""
    
    def test_extraction_result_creation_valid(self):
        """Test creating a valid ExtractionResult."""
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
            total_documents_processed=10,
            documents_with_use_cases=5,
            total_use_cases_found=15,
            final_use_cases=[use_case],
            processing_time_seconds=120.5,
            errors=["Error 1", "Error 2"]
        )
        
        assert result.total_documents_processed == 10
        assert result.documents_with_use_cases == 5
        assert result.total_use_cases_found == 15
        assert len(result.final_use_cases) == 1
        assert result.processing_time_seconds == 120.5
        assert len(result.errors) == 2
    
    def test_extraction_result_empty_use_cases(self):
        """Test ExtractionResult with empty use cases list."""
        result = ExtractionResult(
            total_documents_processed=5,
            documents_with_use_cases=0,
            total_use_cases_found=0,
            final_use_cases=[],
            processing_time_seconds=30.0
        )
        
        assert len(result.final_use_cases) == 0
        assert len(result.errors) == 0  # Default empty list
    
    def test_extraction_result_default_errors(self):
        """Test ExtractionResult with default empty errors list."""
        result = ExtractionResult(
            total_documents_processed=5,
            documents_with_use_cases=2,
            total_use_cases_found=3,
            final_use_cases=[],
            processing_time_seconds=45.0
            # errors not specified - should default to empty list
        )
        
        assert result.errors == []
    
    def test_extraction_result_missing_required_fields(self):
        """Test ExtractionResult creation with missing required fields."""
        with pytest.raises(ValidationError) as excinfo:
            ExtractionResult(
                # Missing all required fields
            )
        
        error = excinfo.value
        assert "total_documents_processed" in str(error)
        assert "documents_with_use_cases" in str(error)
        assert "total_use_cases_found" in str(error)
        assert "final_use_cases" in str(error)
        assert "processing_time_seconds" in str(error)
    
    def test_extraction_result_invalid_types(self):
        """Test ExtractionResult creation with invalid field types."""
        with pytest.raises(ValidationError):
            ExtractionResult(
                total_documents_processed="not_a_number",  # Should be int
                documents_with_use_cases=5,
                total_use_cases_found=3,
                final_use_cases=[],
                processing_time_seconds=45.0
            )
        
        with pytest.raises(ValidationError):
            ExtractionResult(
                total_documents_processed=5,
                documents_with_use_cases=5,
                total_use_cases_found=3,
                final_use_cases="not_a_list",  # Should be list
                processing_time_seconds=45.0
            )
    
    def test_extraction_result_negative_values(self):
        """Test ExtractionResult with edge case values."""
        # Negative values should be accepted (might indicate errors)
        result = ExtractionResult(
            total_documents_processed=0,
            documents_with_use_cases=0,
            total_use_cases_found=0,
            final_use_cases=[],
            processing_time_seconds=0.0
        )
        
        assert result.total_documents_processed == 0
        assert result.documents_with_use_cases == 0
        assert result.total_use_cases_found == 0
        assert result.processing_time_seconds == 0.0
    
    def test_extraction_result_large_processing_time(self):
        """Test ExtractionResult with large processing time."""
        result = ExtractionResult(
            total_documents_processed=1000,
            documents_with_use_cases=500,
            total_use_cases_found=2000,
            final_use_cases=[],
            processing_time_seconds=3600.0  # 1 hour
        )
        
        assert result.processing_time_seconds == 3600.0


if __name__ == "__main__":
    pytest.main([__file__])