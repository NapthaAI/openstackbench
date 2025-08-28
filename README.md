# StackBench

```
███████╗████████╗ █████╗  ██████╗██╗  ██╗██████╗ ███████╗███╗   ██╗ ██████╗██╗  ██╗
██╔════╝╚══██╔══╝██╔══██╗██╔════╝██║ ██╔╝██╔══██╗██╔════╝████╗  ██║██╔════╝██║  ██║
███████╗   ██║   ███████║██║     █████╔╝ ██████╔╝█████╗  ██╔██╗ ██║██║     ███████║
╚════██║   ██║   ██╔══██║██║     ██╔═██╗ ██╔══██╗██╔══╝  ██║╚██╗██║██║     ██╔══██║
███████║   ██║   ██║  ██║╚██████╗██║  ██╗██████╔╝███████╗██║ ╚████║╚██████╗██║  ██║
╚══════╝   ╚═╝   ╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝╚═════╝ ╚══════╝╚═╝  ╚═══╝ ╚═════╝╚═╝  ╚═╝
```

**Benchmark coding agents on library-specific tasks**

Open source local deployment tool for benchmarking coding agents (especially Cursor) on library-specific tasks. Test how well AI coding assistants understand and work with your documentation, APIs, and domain-specific patterns.

## Why did we create StackBench?

StackBench was created in response to the challenges faced by devtool builders in understanding how AI coding agents interact with their software libraries and APIs. Through conversations with dozens of developer-focused companies, we consistently heard that coding agents often use outdated versions, call deprecated functions, or simply get things wrong. Many maintainers didn’t actually know how well these agents were using their libraries at all.

Existing code generation benchmarks typically evaluate models, not agents, and focus on producing self-contained code snippets rather than assessing real usage of library APIs. Almost none focus on library-specific generation tasks—meaning they don’t test whether an agent can solve a task using the actual methods and patterns from your library, rather than writing everything from scratch.

StackBench fills this gap by providing a tool that benchmarks coding agents on real-world, library-specific tasks. It helps maintainers and developers discover failures, spot improvement opportunities, and get actionable insights into how their documentation and APIs are being used by modern AI coding assistants.

## Prerequisites

### System Requirements
- **Python 3.10+**
- **Node.js 18+** (for Claude Code CLI)
- **Git** (for repository operations)

### API Keys Required
- **OpenAI API Key** - For DSPy-powered use case extraction
- **Anthropic API Key** - For Claude Code analysis

### Installation Dependencies

1. **Install uv** (Python package manager):
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

2. **Install Claude Code CLI** (required for analysis):
```bash
npm install -g @anthropic-ai/claude-code
```

## Quick Start

### Installation

```bash
# Clone and install StackBench
git clone https://github.com/your-org/stackbench
cd stackbench
uv sync

# Configure environment variables
cp .env.sample .env
# Edit .env and add your API keys:
# - OPENAI_API_KEY=your_openai_key_here
# - ANTHROPIC_API_KEY=your_anthropic_key_here
```

### Basic Usage

**Streamlined IDE Workflow (Recommended):**
```bash
# 1. Set up repository for IDE execution (clone + extract in one command)
stackbench setup https://github.com/user/awesome-lib -a cursor -l javascript

# 2. Execute use cases manually in Cursor IDE
# ⚠️ Wait for Cursor indexing to complete before implementing!
stackbench print-prompt <run-id> -u 1 --copy
# [Implement in Cursor IDE - repeat for all use cases]

# 3. Analyze results
stackbench analyze <run-id>
```

**Streamlined CLI Workflow (Coming Soon):**
```bash
# Full automation for CLI agents (not yet implemented)
stackbench run https://github.com/user/awesome-lib -a claude-code
```

**Setup Options:**
```bash
# Focus on specific folders  
stackbench setup https://github.com/user/awesome-lib -i docs,examples -a cursor -l python

# Use specific branch and language
stackbench setup https://github.com/user/awesome-lib -b develop -a cursor -l typescript

# Language aliases supported: python/py, javascript/js, typescript/ts
stackbench setup https://github.com/user/react-lib -a cursor -l js
```

## CLI Commands

### Streamlined Workflows

**`stackbench setup <repo-url>`**
Set up repository for IDE execution (clone + extract use cases).

```bash
# Complete IDE setup in one command with language specification
stackbench setup https://github.com/user/awesome-lib -a cursor -l python

# Focus on specific folders with JavaScript library
stackbench setup https://github.com/user/awesome-lib -i docs,examples -a cursor -l js

# Use specific branch with TypeScript
stackbench setup https://github.com/user/awesome-lib -b develop -a cursor -l typescript
```

This command:
- Creates a unique run ID and directory structure
- Clones the repository to `./data/<uuid>/repo/`
- Extracts use cases using DSPy analysis
- Sets up agent configuration
- Shows generated use cases and next steps
- Ready for manual IDE execution

**`stackbench run <repo-url>`** *(Coming Soon)*
Full automated benchmark pipeline for CLI agents.

```bash
# Automated execution (not yet implemented)
stackbench run https://github.com/user/awesome-lib -a claude-code -i docs,examples
```

### Individual Steps

**`stackbench clone <repo-url>`**
Clone a repository and set up a new benchmark run.

```bash
# Clone with agent specification and language
stackbench clone https://github.com/user/awesome-lib -a cursor -i docs,examples -l python

# Clone JavaScript library with specific branch
stackbench clone https://github.com/user/react-lib -a cursor -b develop -l js
```

**`stackbench list`**
List all benchmark runs with their status.

```bash
stackbench list
```

Shows a table with:
- **Run ID**: Full UUID for use with other commands
- **Repository**: Repository name
- **Phase**: Current phase (created → cloned → extracted → execution → analysis_individual → analysis_overall → completed)
- **Agent**: Configured agent type (cursor, claude code, etc.)
- **Created**: Creation timestamp
- **Use Cases**: Number of extracted use cases (— if not extracted yet)
- **Status**: Progress indicators and next steps

**`stackbench status <run-id>`**
Show detailed status and progress for a specific run.

```bash
stackbench status 4a72004a-592b-49b7-9920-08cf54485f85
```

Displays:
- Current phase and timeline
- Individual use case execution/analysis status
- Error tracking
- Suggested next steps based on current state

### Use Case Extraction

**`stackbench extract <run-id>`**
Extract use cases from a cloned repository's documentation.

```bash
# Extract use cases from a run
stackbench extract 4a72004a-592b-49b7-9920-08cf54485f85
```

This command:
- Validates the run is in "cloned" phase
- Uses DSPy to analyze markdown documentation
- Generates library-specific use cases with:
  - Functional requirements
  - User stories  
  - System design guidance
  - Target audience and complexity level
- Updates run phase to "extracted"
- Shows next steps based on agent type

**`stackbench print-prompt <run-id> --use-case <n>`**
Print formatted prompt for manual execution of a specific use case.

```bash
# Print prompt for use case 1
stackbench print-prompt 4a72004a-592b-49b7-9920-08cf54485f85 -u 1

# Print prompt and copy to clipboard automatically
stackbench print-prompt 4a72004a-592b-49b7-9920-08cf54485f85 -u 1 --copy

# Override agent type for different prompt format  
stackbench print-prompt <run-id> -u 2 --agent cursor
```

This command:
- Validates the run has extracted use cases
- Loads the specific use case details
- Formats a comprehensive prompt for the agent type
- **Displays prompt with clear start/end boundaries**
- **Optional clipboard copy** with `--copy/-c` flag
- Shows target directory and next steps
- Currently supports Cursor IDE agent

### Use Case Analysis

**`stackbench analyze <run-id>`**
Analyze use case implementations using Claude Code.

```bash
# Analyze all use cases in a run (default: 3 parallel workers)
stackbench analyze 4a72004a-592b-49b7-9920-08cf54485f85

# Analyze with custom number of parallel workers
stackbench analyze <run-id> --workers 5

# Analyze specific use case only
stackbench analyze <run-id> --use-case 2

# Force re-analysis even if already completed
stackbench analyze <run-id> --force
```

This command:
- **Requires Claude Code CLI**: Install with `npm install -g @anthropic-ai/claude-code`
- **Requires ANTHROPIC_API_KEY**: Set in your environment or .env file
- **Parallel Processing**: Runs 3 use cases concurrently by default (configurable with `--workers`)
- **Resume Capability**: Automatically resumes from where it left off if interrupted
- Tests code executability by running implementation files
- Analyzes library usage patterns (real vs mocked implementations)
- Evaluates documentation consultation from code comments
- Generates structured JSON results and quality assessments
- Updates run phase to "analysis_overall" or "completed"

**`stackbench execute <run-id>`** *(Coming Soon)*
Execute use cases with specified CLI agent.

```bash
# Automated execution (not yet implemented)
stackbench execute <run-id> --agent claude-code
```

**`stackbench clean`**
Clean up old benchmark runs.

```bash
# Remove runs older than 30 days (default)
stackbench clean

# Remove runs older than specific number of days
stackbench clean --older-than 7

# Dry run - see what would be deleted
stackbench clean --dry-run
```

### Workflow Examples

**Streamlined IDE Workflow (Recommended)**:
```bash
# One command setup with language specification
stackbench setup https://github.com/user/lib -i docs -a cursor -l javascript

# Manual execution in IDE
stackbench print-prompt <run-id> -u 1 -c # Get formatted prompt + copy to clipboard
# Paste prompt and implement in Cursor IDE
stackbench print-prompt <run-id> -u 2 -c # Continue with remaining use cases

# Analysis
stackbench analyze <run-id>               # Process results when all complete
```

**Step-by-step Workflow**:
```bash
stackbench clone https://github.com/user/lib -i docs -a cursor -l python
stackbench extract <run-id>               # Generate use cases
stackbench print-prompt <run-id> -u 1 -c # Manual execution...
stackbench analyze <run-id>               # Process results
```

**Automated CLI Workflow** (Future):
```bash
stackbench run https://github.com/user/lib -a claude-code
```

## How It Works

### 1. Repository Setup
StackBench clones your target repository and creates an isolated benchmark environment:

```
./data/<uuid>/
├── repo/              # Cloned repository  
├── data/              # Benchmark data
└── run_context.json   # Complete run state
```

### 2. Agent Types

**IDE Agents** (Manual execution)
- Cursor
- Human interaction through IDE
- Pipeline: `clone → extract → manual execution → analyze`

**CLI Agents** (Automated execution)  
- claude-code
- Fully automated execution
- Pipeline: `clone → extract → execute → analyze`

### 3. Execution Pipeline

Each run progresses through seven distinct phases:
- **created** → **cloned** → **extracted** → **execution** → **analysis_individual** → **analysis_overall** → **completed**

The pipeline adapts based on agent type:
- **IDE agents**: Manual execution with generated prompts (`setup` → manual work → `analyze`)
- **CLI agents**: Fully automated execution (`run` command - coming soon)

## Configuration

StackBench uses Pydantic for configuration management with environment variable support.

### Environment Setup

1. **Copy the sample environment file**:
   ```bash
   cp .env.sample .env
   ```

2. **Add your OpenAI API key** (required for use case extraction):
   ```bash
   OPENAI_API_KEY=your_openai_api_key_here
   ```

3. **Add your Anthropic API key** (required for analysis):
   ```bash
   ANTHROPIC_API_KEY=your_anthropic_api_key_here
   ```

4. **Customize other settings** as needed:
   ```bash
   # Core settings
   DATA_DIR=./custom-data
   NUM_USE_CASES=15
   DEFAULT_AGENT=cursor
   
   # DSPy settings
   DSPY_MODEL=gpt-4o-mini
   DSPY_MAX_TOKENS=10000
   
   # Analysis settings
   ANALYSIS_MAX_WORKERS=3
   CLAUDE_MODEL=claude-sonnet-4
   
   # Logging
   LOG_LEVEL=DEBUG
   ```

See `.env.sample` for all available configuration options with detailed descriptions.

## Development

### Setup
```bash
uv sync
uv pip install -e .
```

### Testing
```bash
uv run pytest tests/                    # Run all tests
uv run pytest tests/test_repository.py  # Run specific tests
uv run pytest -k "test_clone" -v        # Run filtered tests
```

### Guidelines
- Use **Pydantic** for all data models and configuration
- Use **Rich** for CLI interfaces  
- Use **DSPy** for AI-powered components
- Write comprehensive tests with fixtures and mocking
- Follow the established patterns for RunContext and RepositoryManager

## Project Structure

```
stackbench/
├── src/stackbench/
│   ├── cli.py                 # Rich-based CLI
│   ├── config.py             # Pydantic configuration  
│   ├── core/
│   │   ├── run_context.py    # RunContext, RunConfig, RunStatus
│   │   └── repository.py     # RepositoryManager
│   ├── agents/               # Agent implementations
│   ├── extractors/           # Use case extractors
│   └── utils/               # Utilities
├── tests/                   # Test files
└── data/                   # Benchmark runs (git ignored)
```

## Experiment Goals

This project aims to validate several hypotheses:

1. **Library maintainers prefer local deployment** over SaaS solutions
2. **Cursor integration enables obvious failure demonstration** on library-specific tasks  
3. **Open source community will contribute** to expand benchmark coverage
4. **Local deployment removes privacy/security barriers** for enterprise adoption

## Contributing

We welcome contributions! 

- **Agent implementations**: Add evaluation for more coding agents
- **Benchmark tasks**: Add new types of tasks to expand what the benchmark evaluates (e.g. use of APIs via API docs)
- **Metrics**: Enhance quality assessment by adding or improving evaluation metrics

## Status

✅ **Production Ready** - Cursor IDE agent fully implemented with complete workflow support. Looking to add more agents - Claude Code CLI agent coming next.

---
