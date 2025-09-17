# StackBench Analysis JSON Specification

## Overview

This document describes each section of the StackBench analysis JSON output, explaining what each field contains and how it should be interpreted.

## JSON Structure

```json
{
  "use_case_number": 1,
  "use_case_name": "Create an MCP Server",
  "code_executability": { ... },
  "underlying_library_usage": { ... },
  "documentation_tracking": { ... },
  "documentation_assessment": "...",
  "code_implementation_quality": { ... },
  "improvement_recommendations": [ ... ]
}
```

## Section Descriptions

### 1. **Basic Information**

```json
{
  "use_case_number": 1,
  "use_case_name": "Create an MCP Server"
}
```

**Purpose**: Identifies which use case this analysis covers
- `use_case_number`: Sequential number (1-based) of the use case in the benchmark run
- `use_case_name`: Human-readable name of the use case being analyzed

### 2. **Code Executability**

```json
{
  "code_executability": {
    "is_executable": "partial",
    "execution_result": "Comprehensive outcome including all execution details",
    "failure_reason": "Detailed diagnosis with suggested fixes",
    "failure_type": "setup_issue"
  }
}
```

**Purpose**: Evaluates whether the generated code actually runs and functions correctly

#### Fields:
- **`is_executable`**: 
  - `"true"`: Code runs successfully with expected functionality
  - `"partial"`: Code loads/starts but has limitations, or would work with basic setup fixes  
  - `"false"`: Fundamental problems preventing execution

- **`execution_result`**: Comprehensive summary of what happened when running the code
  - Success: Describes functionality that worked
  - Failure: Describes specific error messages and failure points
  - Mixed: Describes what worked and what didn't

- **`failure_reason`**: (Optional) Detailed explanation when code doesn't work
  - Root cause analysis
  - Suggested fixes for resolution
  - Distinction between setup issues vs code logic problems

- **`failure_type`**: (Optional) Categorization of the primary failure
  - `"setup_issue"`: Missing dependencies, environment config, build requirements
  - `"version_issue"`: Package version compatibility problems
  - `"api_compatibility"`: Code uses outdated/incorrect API methods
  - `"infrastructure"`: Requires external services (databases, APIs) not available
  - `"code_logic"`: Fundamental implementation or logical errors

### 3. **Underlying Library Usage**

```json
{
  "underlying_library_usage": {
    "was_used": true,
    "was_mocked": false,
    "mocking_reason": null,
    "mocking_decision_trace": {
      "initial_attempts": ["List of real library attempts"],
      "alternative_approaches": [],
      "final_decision_point": "Why agent chose real vs mock",
      "mock_strategy": null
    }
  }
}
```

**Purpose**: Analyzes whether the implementation uses authentic library APIs or resorts to mocking/fake implementations

#### Fields:
- **`was_used`**: Boolean indicating if the target library was actually used
- **`was_mocked`**: Boolean indicating if mocking/fake implementations were used instead
- **`mocking_reason`**: (Optional) Explanation of why mocking was chosen over real library
- **`mocking_decision_trace`**: Detailed trace of agent's decision-making process
  - `initial_attempts`: What the agent tried first with real libraries
  - `alternative_approaches`: Other approaches considered
  - `final_decision_point`: The reasoning that led to the final choice
  - `mock_strategy`: How mocking was implemented (if applicable)

### 4. **Documentation Tracking**

```json
{
  "documentation_tracking": {
    "files_consulted": [
      "packages/mcp/README.md",
      "docs/src/content/en/reference/tools/mcp-server.mdx"
    ],
    "implementation_notes": [
      "Used real library imports from @mastra/mcp and @mastra/core",
      "Applied MCPServer patterns from official documentation"
    ],
    "evidence_of_usage": "How documentation was applied in the implementation"
  }
}
```

**Purpose**: Tracks what documentation the coding agent consulted and how effectively it was used

#### Fields:
- **`files_consulted`**: List of documentation files referenced in the code
  - Extracted from "DOCUMENTATION CONSULTED" comments in implementation
  - Shows breadth of research conducted

- **`implementation_notes`**: Key decisions and patterns observed in the code
  - How documented patterns were applied
  - Evidence of following library conventions
  - Integration approaches used

- **`evidence_of_usage`**: Narrative assessment of documentation effectiveness
  - How well the agent followed documented examples
  - Whether implementation matches documented best practices
  - Quality of pattern application

### 5. **Documentation Assessment**

```json
{
  "documentation_assessment": "Documentation was comprehensive and accurate - agent successfully consulted 5 relevant files and implementation follows documented patterns exactly. No documentation gaps identified."
}
```

**Purpose**: Brief evaluation of documentation effectiveness for the specific use case

#### Field:
- **`documentation_assessment`**: (Optional) 1-2 sentences about doc effectiveness
  - Whether documentation helped or hindered the implementation
  - Specific gaps or strengths identified
  - Overall assessment of doc quality for this use case
  - Examples:
    - Success: "Documentation was comprehensive with working examples"
    - Failure: "Documentation examples use deprecated APIs not in installed version"

### 6. **Code Implementation Quality**

```json
{
  "code_implementation_quality": {
    "completeness_score": "9 - Implementation fully addresses all functional requirements...",
    "clarity_score": "9 - Code is well-structured with clear separation of concerns...",
    "accuracy_score": "9 - Correctly uses all documented API patterns...",
    "example_quality_score": "9 - Provides complete working example...",
    "overall_score": "9 - Excellent implementation demonstrating deep understanding...",
    "agent_readiness": "ready"
  }
}
```

**Purpose**: Evaluates the quality of the code implementation across multiple dimensions

#### Fields:
All scores are 1-10 with detailed reasoning:

- **`completeness_score`**: Does the code meet all functional requirements?
  - Covers all specified features
  - Handles required use cases
  - Includes necessary error handling

- **`clarity_score`**: How readable and well-structured is the code?
  - Code organization and structure
  - Variable naming and comments
  - Logical flow and modularity

- **`accuracy_score`**: How correctly are libraries and APIs used?
  - Proper API usage patterns
  - Correct method signatures and parameters
  - Following library conventions

- **`example_quality_score`**: Quality of examples and demonstrations
  - Realistic use cases
  - Comprehensive test scenarios
  - Educational value for other developers

- **`overall_score`**: Combined assessment of implementation quality
  - Holistic evaluation considering all factors
  - Production readiness
  - Maintainability and extensibility

- **`agent_readiness`**: Overall readiness assessment
  - `"ready"`: Production-ready implementation
  - `"needs_improvement"`: Good but requires fixes
  - `"not_ready"`: Significant issues preventing use

### 7. **Improvement Recommendations**

```json
{
  "improvement_recommendations": [
    {
      "priority": "low",
      "category": "structure",
      "issue": "Specific problem identified",
      "recommendation": "Specific improvement needed",
      "expected_impact": "How this would help future agents"
    }
  ]
}
```

**Purpose**: Provides specific, actionable recommendations for improving documentation or library design

#### Fields per Recommendation:
- **`priority`**: Urgency level
  - `"critical"`: Blocks agent success, must fix immediately
  - `"high"`: Significantly impacts agent performance
  - `"medium"`: Moderate impact on agent experience  
  - `"low"`: Minor enhancement, nice-to-have

- **`category`**: Type of improvement needed
  - `"missing_info"`: Documentation lacks essential information
  - `"unclear_explanation"`: Documentation is confusing or ambiguous
  - `"poor_examples"`: Examples are inadequate or misleading
  - `"structure"`: Documentation organization needs improvement

- **`issue`**: Specific problem identified in current state

- **`recommendation`**: Concrete action library maintainers should take

- **`expected_impact`**: How this change would improve AI agent success

## Usage Guidelines

### For Library Maintainers
- Focus on `improvement_recommendations` for actionable next steps
- Review `documentation_tracking` to see if agents found your docs
- Check `failure_type` patterns across multiple use cases for systemic issues

### For StackBench Users  
- Use `code_implementation_quality.overall_score` for quick assessment
- Examine `code_executability.failure_reason` to understand what went wrong
- Review `underlying_library_usage` to see if agents resort to mocking

### For Analysis Tools
- `is_executable` provides categorical success status
- `failure_type` enables automated categorization of issues
- All score fields follow consistent 1-10 rating with reasoning format

## Version History

- **V1**: Initial schema with `quality_assessment`, `test_results`, and `failed_due_to_api_key_error` fields
- **V2**: Implemented targeted improvements:
  - **Removed**: `test_results` field (duplicated `execution_result`)
  - **Removed**: `failed_due_to_api_key_error` field (too specific, integrated into `failure_reason`)
  - **Added**: `documentation_assessment` field for explicit doc effectiveness evaluation
  - **Renamed**: `quality_assessment` → `code_implementation_quality` for clarity