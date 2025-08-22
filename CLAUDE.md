# StackBench

StackBench is an open source local deployment tool for benchmarking coding agents (especially Cursor) on library-specific tasks.

## Purpose

To enable library maintainers and enterprise teams to benchmark how well coding agents (e.g. Cursor) perform on library-specific tasks through local deployment and open source community collaboration.

**Library-specific tasks** include:
- Using library APIs correctly (proper imports, method calls, configuration)
- Following library-specific patterns and conventions
- Handling library-specific error cases and edge conditions
- Implementing common use cases as documented in library examples

## Setup

This project uses [uv](https://docs.astral.sh/uv/) for Python package management.

### Prerequisites

Install uv:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Development Setup

1. Initialize the project:
```bash
uv init
```

2. Install dependencies:
```bash
uv sync
```

3. Activate the virtual environment:
```bash
source .venv/bin/activate
```

## Commands

### Package Management
- `uv add <package>` - Add a new dependency
- `uv add --dev <package>` - Add a development dependency
- `uv remove <package>` - Remove a dependency
- `uv sync` - Install/update all dependencies
- `uv lock` - Update the lock file

### Running Code
- `uv run <script>` - Run a Python script
- `uv run python <file>` - Run a Python file
- `uv run pytest` - Run tests

### Environment
- `uv venv` - Create virtual environment
- `source .venv/bin/activate` - Activate environment (Unix)
- `.venv\Scripts\activate` - Activate environment (Windows)

## Project Structure

```
stackbench/
├── src/stackbench/
│   ├── cli.py                    # Rich-based CLI entry point
│   ├── config.py                 # Pydantic configuration models
│   ├── core/
│   │   ├── run_context.py        # Run state management
│   │   └── repository.py         # Git operations and repo management
│   ├── agents/
│   │   ├── base.py              # Abstract agent interface
│   │   ├── openai_agent.py      # OpenAI API integration
│   │   └── cursor_agent.py      # Cursor IDE workflows
│   ├── extractors/
│   │   ├── models.py            # Pydantic models for extraction
│   │   ├── signatures.py        # DSPy signatures
│   │   ├── modules.py           # DSPy modules
│   │   ├── extractor.py         # Main extraction logic
│   │   └── utils.py             # Token counting utilities
│   └── analyzers/
│       └── dspy_analyzer.py     # DSPy-powered performance analysis
├── tests/                       # Test files
├── data/                        # Benchmark run data (git ignored)
├── examples/                    # Example benchmark configs
├── pyproject.toml              # Project configuration
├── uv.lock                     # Lock file (created by uv)
├── .env.example                # Environment variables template
└── README.md                   # Project README
```

## Goals

1. Validate library maintainers prefer local deployment
2. Demonstrate Cursor failures on library-specific tasks
3. Enable community-driven benchmark expansion
4. Remove privacy barriers for enterprise adoption

## Development Guidelines

- **Always use Pydantic** for data models and configuration management
- Use rich for CLI interfaces
- Use dspy for AI-powered components

### Testing Guidelines

- **Write tests for all core functionality** using pytest
- **Use fixtures** for setup/teardown (temp directories, mocked dependencies)
- **Mock external dependencies** (git operations, API calls, file system when appropriate)
- **Test error scenarios** not just happy paths
- **Use descriptive test names** that explain what is being tested
- **Group related tests** in classes (e.g., `TestRunContext`, `TestRepositoryManager`)
- **Test isolation** - each test should run independently
- **Coverage focus** - prioritize testing business logic and error handling over simple getters/setters

### Test Structure
```python
@pytest.fixture
def temp_data_dir():
    """Create temporary directory for test isolation."""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    shutil.rmtree(temp_dir)

class TestClassName:
    def test_specific_functionality(self, fixtures):
        """Test description explaining what is verified."""
        # Arrange, Act, Assert pattern
```

### Running Tests
```bash
uv run pytest tests/                    # Run all tests
uv run pytest tests/test_file.py -v     # Run specific file with verbose output
uv run pytest -k "test_name" -v        # Run specific test
```

## Architecture

### Run Structure
Each benchmark run creates a unique folder in `./data/<uuid>/`:
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

### Run Context & Configuration

Each run maintains comprehensive state in `RunContext`:
- **RunConfig**: Repository URL, include folders, agent type, DSPy settings
- **RunStatus**: Phase tracking, completion flags, execution counts, error logs
- **Directory Management**: Automatic path resolution for repo, data, use case files
- **Persistence**: Auto-saves state changes to `run_context.json`

### Agent Types

**CLI Agents** (automated execution):
- Can run full pipeline: `clone → extract → execute → analyze`
- Each use case prompt specifies target file location (e.g., `./data/<uuid>/data/use_case_1/solution.py`)
- Examples: OpenAI API agents, local LLM agents

**IDE Agents** (manual execution):
- Require human interaction through IDE
- Pipeline: `clone → extract → print use case prompts` (manual execution) → `analyze`
- Each use case prompt specifies target file location (e.g., `./data/<uuid>/data/use_case_1/solution.py`)
- Examples: Cursor, VSCode extensions

### CLI Workflows

**Full Pipeline (CLI agents):**
```bash
stackbench run <repo-url> --agent <cli-agent>  # Complete automation
```

**Manual Pipeline (IDE agents):**
```bash
stackbench init <repo-url> --agent cursor     # Clone + extract + setup
# Manual execution in IDE (copy prompts, create files in use_case_X/ dirs)
stackbench analyze <run-id>                   # Process results
```

**Individual Steps:**
```bash
stackbench clone <repo-url>                       # Clone repository (returns run-id)
stackbench extract <run-id>                       # Generate use cases
stackbench print-prompt <run-id> --use-case <n>   # Print specific use case prompt for manual execution
stackbench execute <run-id> --agent <agent>       # Execute with agent
stackbench analyze <run-id>                       # Generate analysis
stackbench status <run-id>                        # Check run status
stackbench list                                   # List all runs
stackbench clean                                  # Clean up old runs
```

### Run State Management

Runs progress through phases: `created` → `cloned` → `extracted` → `executed` → `analyzed`

Each phase completion is tracked with:
- Timestamps and completion flags
- Execution counts and success rates  
- Error logs with timestamps
- Automatic state persistence

## Analysis & Results Output

### Report Generation
StackBench generates dual output formats for each analysis:
- **results.json**: Structured data for programmatic access and integration
- **results.md**: Human-readable analysis report focusing on specific failure patterns and root causes

### Core Analysis Components

1. **Pass/Fail Flag**: Did coding agents successfully complete library-specific tasks?
2. **Success Rate**: Percentage of use cases completed successfully.
3. **Common Failures**: Top error patterns and failure reasons.

### Report Structure Template

```markdown
# [Library Name] Analysis Report

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

### Manual Execution Workflow

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