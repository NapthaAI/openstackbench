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

### 3. Workflow

```bash
# For IDE agents (like Cursor)
stackbench clone <repo-url> --agent cursor
stackbench extract <run-id>        # Generates use case prompts
# Manual execution in Cursor
stackbench analyze <run-id>        # Process results

# For CLI agents  
stackbench run <repo-url> --agent openai  # Full automation
```

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