"""Pydantic models for analysis results."""

import json
from datetime import datetime
from typing import List, Optional, Union, Literal, Dict, Any
from pydantic import BaseModel, Field


class CodeExecutabilityResult(BaseModel):
    """Results of code execution testing."""
    is_executable: Union[bool, Literal["partial"]]
    execution_result: str
    failure_reason: Optional[str] = None
    failure_type: Optional[Literal["setup_issue", "version_issue", "api_compatibility", "infrastructure", "code_logic"]] = None


class MockingDecisionTrace(BaseModel):
    """Detailed trace of why agent chose to mock instead of using real library."""
    attempt: str
    error_message: str
    agent_response: str


class MockingAnalysis(BaseModel):
    """Analysis of mocking behavior in implementation."""
    initial_attempts: List[str] = Field(default_factory=list, description="List of initial attempts made")
    alternative_approaches: List[str] = Field(default_factory=list, description="List of alternative approaches tried")
    final_decision_point: Optional[str] = None
    mock_strategy: Optional[str] = None


class UnderlyingLibraryUsage(BaseModel):
    """Analysis of library usage patterns."""
    was_used: bool
    was_mocked: bool
    mocking_reason: Optional[str] = None
    mocking_decision_trace: MockingAnalysis = Field(default_factory=MockingAnalysis)


class DocumentationTracking(BaseModel):
    """Documentation tracking and usage analysis."""
    files_consulted: List[str] = Field(default_factory=list, description="List of documentation files referenced in code comments")
    implementation_notes: List[str] = Field(default_factory=list, description="Notes from code comments about implementation decisions")
    evidence_of_usage: str = Field(description="How documentation was applied in the implementation")


class DocumentationStrength(BaseModel):
    """Documentation strength analysis."""
    strength: str
    evidence: str
    impact: str


class DocumentationWeakness(BaseModel):
    """Documentation weakness analysis."""
    weakness: str
    evidence: str
    impact: str


class QualityAssessment(BaseModel):
    """Quality assessment scores."""
    completeness_score: str  # 0-10 with reasoning
    clarity_score: str  # 0-10 with reasoning
    accuracy_score: str  # 0-10 with reasoning
    example_quality_score: str  # 0-10 with reasoning
    overall_score: str  # 0-10 overall assessment
    agent_readiness: str  # ready|needs_improvement|not_ready


class ImprovementRecommendation(BaseModel):
    """Documentation improvement recommendation."""
    priority: str  # critical|high|medium|low
    category: str  # missing_info|unclear_explanation|poor_examples|structure
    issue: str
    recommendation: str
    expected_impact: str


class OverallSummary(BaseModel):
    """Overall summary of benchmark run."""
    pass_fail_status: str  # PASS|FAIL
    success_rate: float
    total_use_cases: int
    successful_cases: int
    failed_cases: int
    analyzed_at: datetime = Field(default_factory=datetime.now)


class CommonFailurePattern(BaseModel):
    """Common failure pattern across use cases."""
    pattern: str
    frequency: int
    examples: List[str] = Field(default_factory=list)
    impact: str


class FrameworkInsight(BaseModel):
    """Framework-specific insights."""
    category: str
    insight: str
    evidence: List[str] = Field(default_factory=list)
    recommendation: str


class UseCaseAnalysisResult(BaseModel):
    """Complete analysis result for a single use case."""
    use_case_number: int
    use_case_name: str
    code_executability: CodeExecutabilityResult
    underlying_library_usage: UnderlyingLibraryUsage
    documentation_tracking: DocumentationTracking
    documentation_assessment: Optional[str] = None
    code_implementation_quality: QualityAssessment
    improvement_recommendations: List[ImprovementRecommendation] = Field(default_factory=list)

    @classmethod
    def generate_json_example(cls) -> str:
        """Generate a JSON example from the Pydantic schema with realistic values."""
        example_data = {
            "use_case_number": 1,
            "use_case_name": "Example Use Case Implementation",
            "code_executability": {
                "is_executable": "true/false/\"partial\"",
                "execution_result": "Success output or error message",
                "failure_reason": "Specific reason if failed (optional)",
                "failure_type": "setup_issue|version_issue|api_compatibility|infrastructure|code_logic (optional)"
            },
            "underlying_library_usage": {
                "was_used": "true/false",
                "was_mocked": "true/false",
                "mocking_reason": "Why mocking was chosen if applicable (optional)",
                "mocking_decision_trace": {
                    "initial_attempts": ["List of initial attempts made"],
                    "alternative_approaches": ["List of alternative approaches tried"],
                    "final_decision_point": "Decision reasoning (optional)",
                    "mock_strategy": "How mocking was implemented (optional)"
                }
            },
            "documentation_tracking": {
                "files_consulted": ["README.md", "docs/api.md", "examples/basic_usage.py"],
                "implementation_notes": ["Notes from code comments about decisions made"],
                "evidence_of_usage": "How documentation was applied in the implementation"
            },
            "documentation_assessment": "Brief evaluation of doc effectiveness for this use case (optional)",
            "code_implementation_quality": {
                "completeness_score": "0-10 with reasoning",
                "clarity_score": "0-10 with reasoning", 
                "accuracy_score": "0-10 with reasoning",
                "example_quality_score": "0-10 with reasoning",
                "overall_score": "0-10 overall assessment",
                "agent_readiness": "ready|needs_improvement|not_ready"
            },
            "improvement_recommendations": [
                {
                    "priority": "critical|high|medium|low",
                    "category": "missing_info|unclear_explanation|poor_examples|structure",
                    "issue": "Specific problem identified",
                    "recommendation": "Specific improvement needed",
                    "expected_impact": "How this would help future agents"
                }
            ]
        }
        return json.dumps(example_data, indent=2)

    @classmethod
    def get_schema_info(cls) -> Dict[str, Any]:
        """Get Pydantic schema information for validation."""
        return cls.model_json_schema()