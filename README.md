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

## Why StackBench?

- 📚 **Library-focused**: Test agents on your specific codebase and documentation
- 🏠 **Local deployment**: Own your benchmarking data, no cloud dependencies  
- ⚡ **Cursor integration**: Optimized for IDE-based coding agents
- 🎯 **Real insights**: Discover obvious failures and improvement opportunities
- 🌍 **Community-driven**: Expandable benchmark library

## Quick Start

### Installation

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and install StackBench
git clone https://github.com/your-org/stackbench
cd stackbench
uv sync
```

### Basic Usage

```bash
# Clone a repository for benchmarking
stackbench clone https://github.com/user/awesome-lib

# Focus on specific folders  
stackbench clone https://github.com/user/awesome-lib -i docs,examples

# Clone specific branch
stackbench clone https://github.com/user/awesome-lib -b develop -i docs,tutorials
```

## CLI Commands

### Repository Management

**`stackbench clone <repo-url>`**
Clone a repository and set up a new benchmark run.

```bash
# Basic clone
stackbench clone https://github.com/user/awesome-lib

# Include specific folders only
stackbench clone https://github.com/user/awesome-lib -i docs,examples

# Clone specific branch
stackbench clone https://github.com/user/awesome-lib -b develop
```

**`stackbench list`**
List all benchmark runs with their status.

```bash
stackbench list
```

Shows a table with:
- **Run ID**: Full UUID for use with other commands
- **Repository**: Repository name
- **Phase**: Current phase (created → cloned → extracted → executed → analyzed)
- **Agent**: Configured agent type (cursor, openai, etc.)
- **Created**: Creation timestamp
- **Use Cases**: Number of extracted use cases (— if not extracted yet)
- **Status**: Success rate and error indicators

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

### Workflow Examples

**Manual IDE Workflow (Cursor)**:
```bash
stackbench clone https://github.com/user/lib -i docs
stackbench list                           # Get run ID
stackbench extract <run-id>               # Generate use cases
stackbench print-prompt <run-id> -u 1 -c # Get formatted prompt + copy to clipboard
# Paste prompt and implement in Cursor IDE
stackbench print-prompt <run-id> -u 2 -c # Continue with remaining use cases
stackbench analyze <run-id>               # Process results when all complete
```

**Automated CLI Workflow** (Future):
```bash
stackbench run https://github.com/user/lib --agent openai
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
- Cursor, VSCode extensions
- Human interaction through IDE
- Pipeline: `clone → extract → manual execution → analyze`

**CLI Agents** (Automated execution)  
- OpenAI API, local LLMs
- Fully automated execution
- Pipeline: `clone → extract → execute → analyze`

### 3. Execution Pipeline

Each run progresses through these phases:
- **created** → **cloned** → **extracted** → **executed** → **analyzed**

The pipeline adapts based on agent type:
- **IDE agents**: Manual execution with generated prompts
- **CLI agents**: Fully automated execution

## Configuration

StackBench uses Pydantic for configuration management with environment variable support:

```bash
# .env file
STACKBENCH_DATA_DIR=./custom-data
STACKBENCH_NUM_USE_CASES=15
STACKBENCH_DSPY_MODEL=gpt-4o-mini
STACKBENCH_LOG_LEVEL=DEBUG
```

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

We welcome contributions! Please see our development guidelines in [CLAUDE.md](CLAUDE.md) for detailed information about:
- Development setup and workflows
- Testing guidelines and patterns
- Architecture decisions and patterns
- Code style and conventions

## License

[Add your license here]

## Status

🚧 **Early Development** - Core repository management and CLI interface complete. Use case extraction and agent execution in development.

---

*Built with ❤️ for the coding agent community*