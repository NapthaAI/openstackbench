"""DSPy signatures for use case extraction."""

import dspy
from typing import List

from .models import UseCase


class DocumentAnalyzer(dspy.Signature):
    """Analyze a document to determine if it contains extractable use cases."""
    
    content: str = dspy.InputField(description="Content of the documentation file")
    
    has_use_cases: bool = dspy.OutputField(
        description="Whether this document contains practical examples or use cases that can be implemented"
    )
    summary: str = dspy.OutputField(
        description="Brief 2-sentence summary of what the document covers"
    )


class UseCaseExtractor(dspy.Signature):
    """Extract actionable use cases from documentation content."""
    
    content: str = dspy.InputField(description="Content of the documentation file")
    source_file: str = dspy.InputField(description="Path of the source documentation file")
    
    use_cases: List[UseCase] = dspy.OutputField(
        description="List of actionable use cases extracted from the documentation. Focus on practical examples that can be implemented by a coding agent."
    )


class UseCaseValidator(dspy.Signature):
    """Validate that a use case is suitable for agent execution."""
    
    use_case: UseCase = dspy.InputField(description="Use case to validate")
    
    is_valid: bool = dspy.OutputField(
        description="Whether this use case is clear, actionable, and suitable for coding agent execution"
    )
    feedback: str = dspy.OutputField(
        description="Brief explanation of why the use case is valid or invalid"
    )