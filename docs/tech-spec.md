## Overview

OpenStackBench is a local CLI tool that benchmarks how well coding agents (starting with Cursor) perform on library-specific tasks. It implements a four-phase pipeline that clones repositories, extracts use cases from documentation, executes benchmarks through coding agents, and analyzes performance results.

## **Architecture & Technology Stack**

### **Core Technologies**

```markdown
- **Python**: Core implementation language with uv package management
- **Rich**: CLI interface with progress bars, tables, and styled output
- **Pydantic**: Configuration management and data validation
- **DSPy**: AI-powered use case extraction and performance analysis
- **GitPython**: Repository cloning and git operations
```

## Workflow Phases

### Phase 1: Repository Cloning

**Purpose**: Clone target repository and prepare workspace

Flow:
- Accept repository URL and optional include folders
- Clone repository to local `./data/<uuid>/repo/` directory
- Create run context with unique UUID and configuration
- Scan for markdown files in specified folders
- Initialize run status tracking

Tools used:
- GitPython for repository operations
- RunContext for state management and persistence

### Phase 2: Use Case Extraction

**Purpose**: Generate realistic coding tasks from library documentation

Flow:
- Scan documentation files (`.md`, `.mdx`) in repository
- Use DSPy-powered AI to analyze content and extract use cases
- Generate diverse use cases covering different complexity levels
- Validate use cases for coding agent executability
- Store use cases as structured JSON in `./data/<uuid>/data/use_cases.json`

Tools used:
- DSPy with OpenAI integration for content analysis
- Pydantic models for use case validation and structure

### **Phase 3: Coding Agent Execution**

**Purpose**: Execute use cases through coding agents and collect results

**CLI Agents (Automated Flow)**:
- Create isolated execution environment per use case
- Execute coding agent with API calls (OpenAI, local LLM)
- Generate solution files in `./data/<uuid>/data/use_case_X/solution.py`
- Log execution output, errors, and performance metrics
- Track completion status and error handling

**IDE Agents (Manual Flow)**:
- Generate formatted prompts for manual execution
- Provide clear instructions for IDE-based development
- Specify target file locations for consistent result collection
- Wait for manual completion before proceeding to analysis

Execution Environment:
```markdown
./data/<uuid>/
├── repo/                    # Cloned repository 
├── data/
│   ├── use_cases.json      # Generated use cases
│   ├── results.json        # Execution results
│   └── use_case_1/         # Individual execution
│       ├── solution.py     # Generated solution
│       ├── output.txt      # Execution output
│       └── errors.txt      # Error logs
└── run_context.json        # Complete run state
```

### **Phase 4: Performance Analysis (Two-Stage Approach)**

**Purpose**: Evaluate coding agent performance on library-specific tasks through comprehensive analysis

#### **Stage 1: Individual Use Case Analysis**

**Flow:**
- Read execution artifacts (code, outputs, error logs) for each use case
- Use Claude Code CLI to analyze individual implementations
- Test generated code for syntax and runtime correctness
- Analyze library usage patterns (real vs mocked implementations)
- Evaluate documentation consultation from code comments
- Generate individual analysis results per use case

**Stage 1 Tools:**
- **Claude Code CLI**: AI-powered code analysis and quality assessment
- **Python execution**: Runtime correctness validation
- **Static analysis**: Library usage pattern detection

#### **Stage 2: Overall Analysis Report Generation**

**Flow:**
- Aggregate individual use case results
- Identify common failure patterns across all use cases
- Calculate success rates and completion metrics
- Generate structured performance assessment
- Create both JSON (programmatic) and Markdown (human-readable) reports

**Stage 2 Tools:**
- **Claude Code CLI**: Pattern recognition and report generation
- **Pydantic models**: Structured data validation and formatting

**Analysis Dimensions:**
- **Code Executability**: Syntax correctness and runtime success
- **Library Usage**: Real API usage vs mocking patterns
- **Documentation Consultation**: Evidence of proper research
- **Quality Assessment**: Overall implementation quality scores
- **Common Failure Patterns**: Systematic issues across use cases

## Implementation Details

### Run Context Management

**RunContext Class**:
- **RunConfig**: Repository URL, include folders, agent type, DSPy settings
- **RunStatus**: Phase tracking (`created` → `cloned` → `extracted` → `executed` → `analyzed`)
- **Directory Management**: Automatic path resolution for all run artifacts
- **Persistence**: Auto-saves state changes to `run_context.json`

### Agent Interface

**Abstract Agent Base Class**:
```python
class Agent:
    def execute_use_case(self, use_case: UseCase, context: RunContext) -> ExecutionResult:
        """Execute a single use case and return results."""
        pass
        
    def can_automate(self) -> bool:
        """Return True if agent supports full automation."""
        pass
```
### CLI Command Structure

**Full Pipeline Commands**:
```bash
stackbench run <repo-url> --agent <cli-agent>     # Full automation
stackbench init <repo-url> --agent cursor         # Manual workflow setup
```

**Step-by-Step Commands**:
```bash
stackbench clone <repo-url>                       # Returns run-id
stackbench extract <run-id>                       # Generate use cases
stackbench print-prompt <run-id> --use-case <n>   # Print specific use case prompt for manual execution
stackbench execute <run-id> --agent <agent>       # Execute with agent
stackbench analyze <run-id>                       # Generate analysis
```

**Management Commands**:
```bash
stackbench status <run-id>                        # Check run status
stackbench list                                   # List all runs
stackbench clean                                  # Clean up old runs
```

## Results Output

### Report File Location
Each run generates both structured data and analysis reports:
- `./data/<uuid>/results.json` - Structured execution results for programmatic access
- `./data/<uuid>/results.md` - Human-readable analysis report

### File Structure Context
```
./data/<uuid>/
├── repo/                    # Cloned repository
├── data/
│   ├── use_cases.json      # Generated use cases
│   ├── results.json        # Structured execution results
│   └── use_case_1/         # Individual execution
│       ├── solution.py     # Generated solution
│       ├── output.txt      # Execution output
│       └── errors.txt      # Error logs
├── run_context.json        # Complete run state
└── results.md              # Generated analysis report
```

### Dual Output Format

**results.json** - Structured data for programmatic access:
```json
{
  "overall_summary": {
    "pass_fail_status": "FAIL",
    "success_rate": 37.5,
    "total_use_cases": 8,
    "successful_cases": 3,
    "failed_cases": 5
  },
  "common_failures": [
    {
      "pattern": "API deprecation",
      "frequency": 3,
      "examples": ["AgentOutput.structured_response", "dict.aput()"]
    }
  ],
  "use_case_results": [...]
}
```

**results.md** - Human-readable analysis with the fundamental components:

1. **Pass/Fail Flag**: Overall success status for the library evaluation
2. **Success Rate**: Percentage and specific numbers (e.g., "37.5% (3/8 tasks)")  
3. **Common Failures**: Top error patterns and failure reasons with examples

### Report Structure Template

```markdown
# [Library Name] Analysis Report

**Experiment:** E002-OpenStackBench  
**Date:** [Date]  
**Pass/Fail Status:** [PASS/FAIL]
**Success Rate:** [X/Y tasks successful (Z%)]

## Executive Summary
- Overall pass/fail determination
- Success rate with specific numbers
- Primary failure patterns identified

## Common Failures Analysis
### [Specific Error Pattern] (e.g., "API Deprecation Issues")
- Detailed breakdown of failure cases
- Root cause analysis with code examples
- Pattern recognition across multiple use cases

## Framework-Specific Insights
- API evolution and breaking changes
- Documentation quality issues
- Systematic problems affecting coding agents
```

## IDE Agent Manual Execution

### Overview
Unlike CLI agents that execute autonomously, IDE agents (like Cursor) require **human operators** to manually interact with the IDE interface. This human-in-the-loop approach evaluates how effectively coding agents assist developers through chat interfaces and inline suggestions.

### Manual Execution Workflow

#### Workflow Steps

**1. Environment Setup (Automated)**
```bash
stackbench clone <repo-url>                         # Clone repository and get run-id
stackbench extract <run-id>                         # Generate use cases
stackbench print-prompt <run-id> --use-case 1       # Print first use case prompt
```

**2. Manual IDE Interaction (Human-Driven)**
- Open prepared repository in IDE (Cursor, VS Code, etc.)
- For each use case:
  - Run `stackbench print-prompt <run-id> --use-case <n>` to get the specific prompt
  - Start new chat session with coding agent
  - Copy/paste the printed use case prompt
  - Allow agent to explore repository and propose solutions
  - Accept/modify suggested changes based on technical merit
  - Save solution in `./data/<uuid>/data/use_case_<n>/solution.py`
  - Repeat for all use cases

**3. Results Collection (Automated)**
```bash
stackbench analyze <run-id>  # Process completed manual execution results
```

## Development Guidelines

### Core Principles

- **Pydantic First**: All configuration and data models use Pydantic validation
- **Rich CLI**: Consistent styling and progress indication using Rich library
- **Local-First**: All data and execution remains on local machine
- **Plugin Architecture**: Extensible agent system for community contributions

### File Organization

```
src/stackbench/
├── cli.py                    # Rich-based CLI entry point
├── config.py                 # Pydantic configuration models
├── core/
│   ├── run_context.py        # Run state management
│   └── repository.py         # Git operations and repo management
├── agents/
│   ├── base.py              # Abstract agent interface
│   ├── openai_agent.py      # OpenAI API integration
│   └── cursor_agent.py      # Cursor IDE workflows
├── extractors/
│   └── dspy_extractor.py    # DSPy-powered use case extraction
└── analyzers/
    └── dspy_analyzer.py         # DSPy-powered performance analysis
```