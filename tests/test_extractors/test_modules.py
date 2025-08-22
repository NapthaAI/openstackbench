"""Tests for DSPy modules integration."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from pydantic import ValidationError

from stackbench.extractors.models import Document, UseCase
from stackbench.extractors.modules import DocumentProcessor


class TestDocumentProcessor:
    """Test DocumentProcessor DSPy integration."""
    
    @pytest.fixture
    def sample_document(self):
        """Create a sample document for testing."""
        return Document(
            file_path=Path("/test/sample.md"),
            content="# Sample Document\n\nThis is a sample document with code examples.",
            truncated_content="# Sample Document\n\nThis is a sample document.",
            num_tokens=20
        )
    
    @pytest.fixture
    def sample_use_case(self):
        """Create a sample use case for testing."""
        return UseCase(
            name="Sample Use Case",
            elevator_pitch="This demonstrates basic functionality",
            target_audience="Developers",
            functional_requirements=["Must work correctly", "Should be simple"],
            user_stories=["As a developer, I want to use this feature"],
            system_design="Simple CLI application",
            architecture_pattern="Command pattern",
            complexity_level="Beginner",
            source_document=["/test/sample.md"],
            real_world_scenario="Building a simple tool",
            target_file="solution.py"
        )
    
    @pytest.fixture
    def processor(self):
        """Create a DocumentProcessor instance."""
        return DocumentProcessor()
    
    def test_processor_initialization(self, processor):
        """Test that DocumentProcessor initializes correctly."""
        assert processor.analyzer is not None
        assert processor.extractor is not None
        assert processor.validator is not None
    
    @patch('dspy.ChainOfThought')
    def test_analyze_document_with_use_cases(self, mock_chain_of_thought, processor, sample_document):
        """Test document analysis when document contains use cases."""
        # Mock the analyzer response
        mock_analyzer = Mock()
        mock_analyzer.return_value = Mock(
            has_use_cases=True,
            summary="Document contains practical examples"
        )
        mock_chain_of_thought.return_value = mock_analyzer
        
        # Re-initialize processor with mocked analyzer
        processor.analyzer = mock_analyzer
        
        has_use_cases, summary = processor.analyze_document(sample_document)
        
        assert has_use_cases is True
        assert summary == "Document contains practical examples"
        mock_analyzer.assert_called_once_with(content=sample_document.truncated_content)
    
    @patch('dspy.ChainOfThought')
    def test_analyze_document_without_use_cases(self, mock_chain_of_thought, processor, sample_document):
        """Test document analysis when document doesn't contain use cases."""
        # Mock the analyzer response
        mock_analyzer = Mock()
        mock_analyzer.return_value = Mock(
            has_use_cases=False,
            summary="Document is purely theoretical"
        )
        mock_chain_of_thought.return_value = mock_analyzer
        
        processor.analyzer = mock_analyzer
        
        has_use_cases, summary = processor.analyze_document(sample_document)
        
        assert has_use_cases is False
        assert summary == "Document is purely theoretical"
    
    @patch('dspy.ChainOfThought')
    def test_analyze_document_error_handling(self, mock_chain_of_thought, processor, sample_document):
        """Test document analysis error handling."""
        # Mock the analyzer to raise an exception
        mock_analyzer = Mock()
        mock_analyzer.side_effect = Exception("DSPy analysis failed")
        mock_chain_of_thought.return_value = mock_analyzer
        
        processor.analyzer = mock_analyzer
        
        has_use_cases, summary = processor.analyze_document(sample_document)
        
        assert has_use_cases is False
        assert "Analysis failed: DSPy analysis failed" in summary
    
    @patch('dspy.ChainOfThought')
    def test_extract_use_cases_success(self, mock_chain_of_thought, processor, sample_document, sample_use_case):
        """Test successful use case extraction."""
        # Mock the extractor response
        mock_extractor = Mock()
        mock_extractor.return_value = Mock(
            use_cases=[sample_use_case]
        )
        mock_chain_of_thought.return_value = mock_extractor
        
        processor.extractor = mock_extractor
        
        use_cases = processor.extract_use_cases(sample_document)
        
        assert len(use_cases) == 1
        assert use_cases[0].name == "Sample Use Case"
        assert use_cases[0].source_document == ["/test/sample.md"]
        assert use_cases[0].target_file == "solution.py"
        
        mock_extractor.assert_called_once_with(
            content=sample_document.truncated_content,
            source_file=str(sample_document.file_path)
        )
    
    @patch('dspy.ChainOfThought')
    def test_extract_use_cases_sets_source_document(self, mock_chain_of_thought, processor, sample_document):
        """Test that source_document is set when missing."""
        # Test that the processor correctly handles source_document setting
        # We need to test the actual logic by mocking the return value correctly
        
        mock_extractor = Mock()
        
        # Create a mock result with use case that has empty source_document
        # We'll create the UseCase with minimal valid data, then mock its source_document as empty
        mock_use_case = Mock()
        mock_use_case.source_document = []  # Empty source_document should be updated
        mock_use_case.target_file = ""      # Empty target_file should be generated
        
        mock_extractor.return_value = Mock(use_cases=[mock_use_case])
        processor.extractor = mock_extractor
        
        use_cases = processor.extract_use_cases(sample_document)
        
        assert len(use_cases) == 1
        # Verify the source_document was set
        assert mock_use_case.source_document == [str(sample_document.file_path)]
        # Verify target_file was generated
        assert mock_use_case.target_file == "use_case_1/solution.py"
    
    @patch('dspy.ChainOfThought')
    def test_extract_use_cases_generates_target_file(self, mock_chain_of_thought, processor, sample_document):
        """Test that target_file is generated when missing."""
        # Create use case without target_file
        use_case_without_target = UseCase(
            name="Test",
            elevator_pitch="Test pitch",
            target_audience="Developers",
            functional_requirements=["Requirement 1"],
            user_stories=["User story 1"],
            system_design="Design",
            architecture_pattern="Pattern",
            complexity_level="Beginner",
            source_document=["/test/doc.md"],
            real_world_scenario="Scenario",
            target_file=""  # Empty target file
        )
        
        mock_extractor = Mock()
        mock_extractor.return_value = Mock(use_cases=[use_case_without_target])
        processor.extractor = mock_extractor
        
        use_cases = processor.extract_use_cases(sample_document)
        
        assert len(use_cases) == 1
        assert use_cases[0].target_file == "use_case_1/solution.py"
    
    @patch('dspy.ChainOfThought')
    def test_extract_use_cases_error_handling(self, mock_chain_of_thought, processor, sample_document):
        """Test use case extraction error handling."""
        mock_extractor = Mock()
        mock_extractor.side_effect = Exception("Extraction failed")
        processor.extractor = mock_extractor
        
        use_cases = processor.extract_use_cases(sample_document)
        
        assert use_cases == []
    
    def test_validate_use_case_complete(self, processor, sample_use_case):
        """Test validation of complete use case."""
        is_valid, feedback = processor.validate_use_case(sample_use_case)
        
        # Basic validation should pass for complete use case
        # Note: DSPy validation is mocked separately
        assert isinstance(is_valid, bool)
        assert isinstance(feedback, str)
    
    def test_validate_use_case_missing_name(self, processor):
        """Test validation fails for use case missing name."""
        incomplete_use_case = UseCase(
            name="",  # Empty name
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
        
        is_valid, feedback = processor.validate_use_case(incomplete_use_case)
        
        assert is_valid is False
        assert "Missing name or elevator_pitch" in feedback
    
    def test_validate_use_case_missing_requirements(self, processor):
        """Test validation fails for use case missing requirements."""
        # Since Pydantic now validates empty lists, we test the validation logic directly
        with pytest.raises(ValidationError) as exc_info:
            UseCase(
                name="Test",
                elevator_pitch="Test pitch",
                target_audience="Developers",
                functional_requirements=[],  # Empty requirements - should fail Pydantic validation
                user_stories=["User story 1"],
                system_design="Design",
                architecture_pattern="Pattern",
                complexity_level="Beginner",
                source_document=["/test/doc.md"],
                real_world_scenario="Scenario"
            )
        
        assert "List cannot be empty" in str(exc_info.value)
    
    def test_validate_use_case_missing_user_stories(self, processor):
        """Test validation fails for use case missing user stories."""
        # Since Pydantic now validates empty lists, we test the validation logic directly
        with pytest.raises(ValidationError) as exc_info:
            UseCase(
                name="Test",
                elevator_pitch="Test pitch",
                target_audience="Developers",
                functional_requirements=["Requirement 1"],
                user_stories=[],  # Empty user stories - should fail Pydantic validation
                system_design="Design",
                architecture_pattern="Pattern",
                complexity_level="Beginner",
                source_document=["/test/doc.md"],
                real_world_scenario="Scenario"
            )
        
        assert "List cannot be empty" in str(exc_info.value)
    
    def test_validate_use_case_missing_system_design(self, processor):
        """Test validation fails for use case missing system design."""
        incomplete_use_case = UseCase(
            name="Test",
            elevator_pitch="Test pitch",
            target_audience="Developers",
            functional_requirements=["Requirement 1"],
            user_stories=["User story 1"],
            system_design="",  # Empty system design
            architecture_pattern="Pattern",
            complexity_level="Beginner",
            source_document=["/test/doc.md"],
            real_world_scenario="Scenario"
        )
        
        is_valid, feedback = processor.validate_use_case(incomplete_use_case)
        
        assert is_valid is False
        assert "No system design provided" in feedback
    
    @patch('dspy.ChainOfThought')
    def test_validate_use_case_dspy_validation(self, mock_chain_of_thought, processor, sample_use_case):
        """Test DSPy validation step."""
        # Mock successful basic validation, then test DSPy validation
        mock_validator = Mock()
        mock_validator.return_value = Mock(
            is_valid=True,
            feedback="Use case is well structured"
        )
        processor.validator = mock_validator
        
        is_valid, feedback = processor.validate_use_case(sample_use_case)
        
        assert is_valid is True
        assert feedback == "Use case is well structured"
        mock_validator.assert_called_once_with(use_case=sample_use_case)
    
    @patch('dspy.ChainOfThought')
    def test_validate_use_case_dspy_error(self, mock_chain_of_thought, processor, sample_use_case):
        """Test DSPy validation error handling."""
        mock_validator = Mock()
        mock_validator.side_effect = Exception("Validation service failed")
        processor.validator = mock_validator
        
        is_valid, feedback = processor.validate_use_case(sample_use_case)
        
        assert is_valid is False
        assert "Validation error: Validation service failed" in feedback
    
    @patch('dspy.ChainOfThought')
    def test_process_document_full_pipeline_success(self, mock_chain_of_thought, processor, sample_document, sample_use_case):
        """Test full document processing pipeline with successful outcome."""
        # Mock analyzer to return has_use_cases=True
        mock_analyzer = Mock()
        mock_analyzer.return_value = Mock(
            has_use_cases=True,
            summary="Document has examples"
        )
        
        # Mock extractor to return use cases
        mock_extractor = Mock()
        mock_extractor.return_value = Mock(use_cases=[sample_use_case])
        
        # Mock validator to return valid
        mock_validator = Mock()
        mock_validator.return_value = Mock(
            is_valid=True,
            feedback="Valid use case"
        )
        
        processor.analyzer = mock_analyzer
        processor.extractor = mock_extractor
        processor.validator = mock_validator
        
        result = processor.process_document(sample_document)
        
        assert len(result) == 1
        assert result[0].name == "Sample Use Case"
    
    @patch('dspy.ChainOfThought')
    def test_process_document_no_use_cases(self, mock_chain_of_thought, processor, sample_document):
        """Test full pipeline when document has no use cases."""
        # Mock analyzer to return has_use_cases=False
        mock_analyzer = Mock()
        mock_analyzer.return_value = Mock(
            has_use_cases=False,
            summary="Document is theoretical only"
        )
        
        processor.analyzer = mock_analyzer
        
        result = processor.process_document(sample_document)
        
        assert result == []
    
    @patch('dspy.ChainOfThought')
    def test_process_document_extraction_fails(self, mock_chain_of_thought, processor, sample_document):
        """Test full pipeline when extraction fails."""
        # Mock analyzer to return has_use_cases=True
        mock_analyzer = Mock()
        mock_analyzer.return_value = Mock(
            has_use_cases=True,
            summary="Document has examples"
        )
        
        # Mock extractor to return empty list
        mock_extractor = Mock()
        mock_extractor.return_value = Mock(use_cases=[])
        
        processor.analyzer = mock_analyzer
        processor.extractor = mock_extractor
        
        result = processor.process_document(sample_document)
        
        assert result == []
    
    @patch('dspy.ChainOfThought')
    def test_process_document_validation_fails(self, mock_chain_of_thought, processor, sample_document, sample_use_case):
        """Test full pipeline when validation fails."""
        # Mock successful analysis and extraction
        mock_analyzer = Mock()
        mock_analyzer.return_value = Mock(
            has_use_cases=True,
            summary="Document has examples"
        )
        
        mock_extractor = Mock()
        mock_extractor.return_value = Mock(use_cases=[sample_use_case])
        
        # Mock validator to return invalid
        mock_validator = Mock()
        mock_validator.return_value = Mock(
            is_valid=False,
            feedback="Use case is incomplete"
        )
        
        processor.analyzer = mock_analyzer
        processor.extractor = mock_extractor
        processor.validator = mock_validator
        
        result = processor.process_document(sample_document)
        
        assert result == []


if __name__ == "__main__":
    pytest.main([__file__])