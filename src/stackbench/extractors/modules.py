"""DSPy modules for document processing and use case extraction."""

import dspy
from typing import List, Tuple

from .models import Document, UseCase
from .signatures import DocumentAnalyzer, UseCaseExtractor, UseCaseValidator


class DocumentProcessor(dspy.Module):
    """Process documents to extract and validate use cases."""
    
    def __init__(self):
        self.analyzer = dspy.ChainOfThought(DocumentAnalyzer)
        self.extractor = dspy.ChainOfThought(UseCaseExtractor)
        self.validator = dspy.ChainOfThought(UseCaseValidator)
    
    def analyze_document(self, document: Document) -> Tuple[bool, str]:
        """Analyze if document contains extractable use cases."""
        try:
            result = self.analyzer(content=document.truncated_content)
            return result.has_use_cases, result.summary
        except Exception as e:
            print(f"Error analyzing {document.file_path}: {e}")
            return False, f"Analysis failed: {e}"
    
    def extract_use_cases(self, document: Document) -> List[UseCase]:
        """Extract use cases from a document."""
        try:
            result = self.extractor(
                content=document.truncated_content,
                source_file=str(document.file_path)
            )
            
            # Ensure use cases have proper source_document and generate target_file
            use_cases = []
            for i, use_case in enumerate(result.use_cases, 1):
                # Set source_document if not already set
                if not use_case.source_document:
                    use_case.source_document = [str(document.file_path)]
                
                # Generate target_file if not set
                if not use_case.target_file:
                    use_case.target_file = f"use_case_{i}/solution.py"
                
                use_cases.append(use_case)
            
            return use_cases
        except Exception as e:
            print(f"Error extracting use cases from {document.file_path}: {e}")
            return []
    
    def validate_use_case(self, use_case: UseCase) -> Tuple[bool, str]:
        """Validate that a use case is suitable for agent execution."""
        try:
            # Basic validation checks first
            if not use_case.name or not use_case.elevator_pitch:
                return False, "Missing name or elevator_pitch"
            
            if not use_case.functional_requirements or len(use_case.functional_requirements) == 0:
                return False, "No functional requirements provided"
            
            if not use_case.user_stories or len(use_case.user_stories) == 0:
                return False, "No user stories provided"
            
            if not use_case.system_design:
                return False, "No system design provided"
            
            if not use_case.target_file:
                return False, "No target file specified"
            
            # DSPy validation
            result = self.validator(use_case=use_case)
            return result.is_valid, result.feedback
        except Exception as e:
            return False, f"Validation error: {e}"
    
    def process_document(self, document: Document) -> List[UseCase]:
        """Full pipeline: analyze, extract, and validate use cases from a document."""
        # Step 1: Analyze if document has use cases
        has_use_cases, summary = self.analyze_document(document)
        
        if not has_use_cases:
            return []
        
        # Step 2: Extract use cases
        raw_use_cases = self.extract_use_cases(document)
        
        if not raw_use_cases:
            return []
        
        # Step 3: Validate use cases
        validated_use_cases = []
        for use_case in raw_use_cases:
            is_valid, feedback = self.validate_use_case(use_case)
            if is_valid:
                validated_use_cases.append(use_case)
            else:
                print(f"Use case '{use_case.name}' validation failed: {feedback}")
        
        return validated_use_cases