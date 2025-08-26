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
│   │   └── cursor_ide.py        # Cursor IDE workflows
│   ├── extractors/
│   │   ├── models.py            # Pydantic models for extraction
│   │   ├── signatures.py        # DSPy signatures
│   │   ├── modules.py           # DSPy modules
│   │   ├── extractor.py         # Main extraction logic
│   │   └── utils.py             # Token counting utilities
│   └── analyzers/
│       ├── individual_analyzer.py  # Individual use case analysis
│       ├── overall_analyzer.py     # Overall analysis report generation
│       └── models.py               # Analysis data models
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

## Architecture

### Run Structure
Each benchmark run creates a unique folder in `./data/<uuid>/`:
```
./data/<uuid>/
├── repo/                    # Cloned repository 
├── data/
│   ├── use_cases.json      # Generated use cases
│   └── use_case_1/         # Individual execution
│       ├── solution.py     # Generated solution
│       ├── output.txt      # Execution output
│       └── errors.txt      # Error logs
├── run_context.json        # Complete run state
└── results.json            # Generated analysis report
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

Runs progress through seven distinct phases: `created` → `cloned` → `extracted` → `execution` → `analysis_individual` → `analysis_overall` → `completed`

#### Phase Descriptions

Each phase represents **completed** work, not work in progress:

- **`created`**: Initial run context established with UUID and directory structure
- **`cloned`**: Repository successfully cloned to local workspace
- **`extracted`**: Use cases generated and saved to `use_cases.json`
- **`execution`**: All use cases executed (either via CLI automation or IDE manual completion)
- **`analysis_individual`**: Individual analysis completed for all executed use cases
- **`analysis_overall`**: Overall analysis report (`results.json` + `results.md`) generated
- **`completed`**: Full benchmark run finished

#### Granular State Tracking

Each phase completion is tracked with comprehensive state management:

**Run-Level Tracking:**
- Phase progression with automatic transitions based on completion criteria
- Timestamps for creation and last update
- Boolean completion flags for each major phase
- Error logs with timestamps
- Automatic state persistence to `run_context.json`

**Use Case-Level Tracking:**
Each individual use case maintains detailed state:
- **Execution Status**: `not_executed`, `executed`, `failed`, `skipped`
- **Analysis Status**: `not_analyzed`, `analyzed`, `failed`  
- **Execution Method**: `ide_manual` (human-driven) or `cli_automated`
- **File Tracking**: Implementation and analysis file existence validation
- **Timestamps**: Execution and analysis completion times
- **Error Tracking**: Specific errors per use case with timestamps

#### Automatic Phase Progression

The system automatically advances phases when completion criteria are met:
- **To `execution`**: When all use cases are executed (success or failure)
- **To `analysis_individual`**: When all executable use cases have been analyzed
- **To `analysis_overall`**: When individual analyses are complete and overall report is generated
- **To `completed`**: When all work is finished

This enables both automated CLI workflows and manual IDE workflows to progress through the same structured state management system.

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