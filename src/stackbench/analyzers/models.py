"""Pydantic models for analysis results."""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class CodeExecutabilityResult(BaseModel):
    """Results of code execution testing."""
    is_executable: bool
    execution_result: str
    failure_reason: Optional[str] = None
    test_results: Optional[str] = None
    failed_due_to_api_key_error: bool = False


class MockingDecisionTrace(BaseModel):
    """Detailed trace of why agent chose to mock instead of using real library."""
    attempt: str
    error_message: str
    agent_response: str


class MockingAnalysis(BaseModel):
    """Analysis of mocking behavior in implementation."""
    initial_attempts: List[MockingDecisionTrace] = Field(default_factory=list)
    alternative_approaches: List[str] = Field(default_factory=list)
    final_decision_point: Optional[str] = None
    mock_strategy: Optional[str] = None


class UnderlyingLibraryUsage(BaseModel):
    """Analysis of library usage patterns."""
    was_used: bool
    was_mocked: bool
    mocking_reason: Optional[str] = None
    mocking_decision_trace: MockingAnalysis = Field(default_factory=MockingAnalysis)


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