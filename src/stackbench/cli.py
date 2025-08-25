"""Rich-based CLI for StackBench."""

import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import click
from rich.console import Console
from rich.table import Table

from .config import get_config
from .core.repository import RepositoryManager
from .core.run_context import RunContext
from .extractors.extractor import extract_use_cases
from .agents.cursor_ide import CursorIDEAgent
from .analyzers.claude_analyzer import ClaudeAnalyzer

console = Console()

STACKBENCH_LOGO = """
[bold cyan]
 ███████╗████████╗ █████╗  ██████╗██╗  ██╗██████╗ ███████╗███╗   ██╗ ██████╗██╗  ██╗
 ██╔════╝╚══██╔══╝██╔══██╗██╔════╝██║ ██╔╝██╔══██╗██╔════╝████╗  ██║██╔════╝██║  ██║
 ███████╗   ██║   ███████║██║     █████╔╝ ██████╔╝█████╗  ██╔██╗ ██║██║     ███████║
 ╚════██║   ██║   ██╔══██║██║     ██╔═██╗ ██╔══██╗██╔══╝  ██║╚██╗██║██║     ██╔══██║
 ███████║   ██║   ██║  ██║╚██████╗██║  ██╗██████╔╝███████╗██║ ╚████║╚██████╗██║  ██║
 ╚══════╝   ╚═╝   ╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝╚═════╝ ╚══════╝╚═╝  ╚═══╝ ╚═════╝╚═╝  ╚═╝
[/bold cyan]
[dim]Benchmark coding agents on library-specific tasks[/dim]
"""


def show_logo():
    """Show the StackBench logo."""
    console.print(STACKBENCH_LOGO)


def parse_include_folders(include_folders_str: str) -> List[str]:
    """Parse comma-separated include folders string."""
    if not include_folders_str:
        return []
    return [folder.strip() for folder in include_folders_str.split(",") if folder.strip()]


def get_phase_color(phase: str) -> str:
    """Get color for phase status."""
    color_map = {
        "created": "dim",
        "cloned": "blue", 
        "extracted": "yellow",
        "executed": "cyan",
        "analyzed": "green",
        "completed": "bold green",
        "failed": "bold red"
    }
    return color_map.get(phase, "white")


def format_datetime(dt_str: str) -> str:
    """Format datetime string for display."""
    try:
        dt = datetime.fromisoformat(dt_str)
        return dt.strftime("%Y-%m-%d %H:%M")
    except:
        return dt_str


def show_help_with_logo(ctx, param, value):
    """Custom help callback that shows logo."""
    if not value or ctx.resilient_parsing:
        return
    show_logo()
    print()
    click.echo(ctx.get_help())
    ctx.exit()


@click.group(invoke_without_command=True)
@click.version_option()
@click.option('--help', '-h', is_flag=True, expose_value=False, is_eager=True, 
              callback=show_help_with_logo, help='Show this message and exit.')
@click.pass_context
def cli(ctx):
    """StackBench - Open source local deployment tool for benchmarking coding agents."""
    if ctx.invoked_subcommand is None:
        show_logo()
        print()  # Add spacing after logo
        click.echo(ctx.get_help())


@cli.command()
@click.argument("repo_url")
@click.option(
    "--include-folders", "-i",
    default="", 
    help="Comma-separated list of folders to include (e.g., docs,examples,tests)"
)
@click.option(
    "--branch", "-b",
    default="main",
    help="Git branch to clone (default: main)"
)
def clone(repo_url: str, include_folders: str, branch: str):
    """Clone a repository and set up a new benchmark run."""
    show_logo()
    try:
        with console.status("[bold green]Cloning repository..."):
            repo_manager = RepositoryManager()
            parsed_folders = parse_include_folders(include_folders)
            
            context = repo_manager.clone_repository(
                repo_url=repo_url,
                include_folders=parsed_folders,
                branch=branch
            )
        
        console.print(f"[bold green]✓[/bold green] Repository cloned successfully!")
        console.print(f"[bold blue]Run ID:[/bold blue] {context.run_id}")
        
        # Find markdown files
        md_files = repo_manager.find_markdown_files(context)
        console.print(f"[yellow]Found {len(md_files)} markdown files[/yellow]")
        
        for file_path in md_files[:5]:  # Show first 5 files
            relative_path = file_path.relative_to(context.repo_dir)
            console.print(f"  • {relative_path}")
        
        if len(md_files) > 5:
            console.print(f"  ... and {len(md_files) - 5} more files")
        
    except Exception as e:
        console.print(f"[bold red]✗[/bold red] Failed to clone repository: {e}")
        sys.exit(1)


@cli.command("list")
def list_runs():
    """List all benchmark runs with their status."""
    try:
        repo_manager = RepositoryManager()
        run_ids = repo_manager.list_runs()
        
        if not run_ids:
            console.print("[yellow]No benchmark runs found.[/yellow]")
            console.print("[dim]Use 'stackbench clone <repo-url>' to create a new run.[/dim]")
            return
        
        # Create table
        table = Table(title="StackBench Runs")
        table.add_column("Run ID", style="cyan", width=36)
        table.add_column("Repository", style="magenta")
        table.add_column("Phase", style="white")
        table.add_column("Agent", style="blue")
        table.add_column("Created", style="dim")
        table.add_column("Use Cases", style="green", justify="right")
        table.add_column("Status", style="white")
        
        # Load run contexts and sort by creation date (newest first)
        runs_data = []
        for run_id in run_ids:
            try:
                context = RunContext.load(run_id)
                summary = context.to_summary_dict()
                runs_data.append((summary, context))
            except Exception as e:
                console.print(f"[red]Warning: Could not load run {run_id}: {e}[/red]")
                continue
        
        # Sort by creation date (newest first)
        runs_data.sort(key=lambda x: x[1].status.created_at, reverse=True)
        
        # Add rows to table
        for summary, context in runs_data:
            full_run_id = summary["run_id"]
            phase_colored = f"[{get_phase_color(summary['phase'])}]{summary['phase']}[/{get_phase_color(summary['phase'])}]"
            
            # Status column
            status_parts = []
            if summary["has_errors"]:
                status_parts.append("[red]⚠ errors[/red]")
            if summary["total_use_cases"] > 0:
                success_rate = summary["success_rate"]
                if success_rate > 0:
                    status_parts.append(f"[green]{success_rate:.0%} success[/green]")
            
            status = " | ".join(status_parts) if status_parts else "[dim]—[/dim]"
            
            table.add_row(
                full_run_id,
                summary["repo_name"],
                phase_colored,
                summary["agent_type"],
                format_datetime(summary["created_at"]),
                str(summary["total_use_cases"]) if summary["total_use_cases"] > 0 else "[dim]—[/dim]",
                status
            )
        
        console.print(table)
        console.print(f"\n[dim]Showing {len(runs_data)} runs. Use 'stackbench extract <run-id>' to generate use cases.[/dim]")
        
    except Exception as e:
        console.print(f"[bold red]✗[/bold red] Failed to list runs: {e}")
        sys.exit(1)


@cli.command()
@click.argument("run_id")
def extract(run_id: str):
    """Extract use cases from a cloned repository."""
    show_logo()
    try:
        # Load run context
        context = RunContext.load(run_id)
        
        # Validate run phase
        if context.status.phase != "cloned":
            console.print(f"[bold red]✗[/bold red] Run must be in 'cloned' phase, currently: {context.status.phase}")
            if context.status.phase == "created":
                console.print("[dim]Use 'stackbench clone <repo-url>' first to clone the repository.[/dim]")
            elif context.status.phase == "extracted":
                console.print("[dim]Use cases already extracted. Use 'stackbench list' to see details.[/dim]")
            sys.exit(1)
        
        console.print(f"[bold blue]Extracting use cases from:[/bold blue] {context.repo_name}")
        console.print(f"[dim]Run ID: {context.run_id}[/dim]")
        console.print(f"[dim]Repository: {context.config.repo_url}[/dim]")
        
        if context.config.include_folders:
            console.print(f"[dim]Include folders: {', '.join(context.config.include_folders)}[/dim]")
        
        console.print()
        
        # Run extraction with progress indication
        with console.status("[bold green]Setting up DSPy and analyzing documents..."):
            try:
                result = extract_use_cases(context)
            except Exception as e:
                console.print(f"[bold red]✗[/bold red] Extraction failed: {e}")
                context.add_error(f"Extraction failed: {str(e)}")
                sys.exit(1)
        
        # Display results
        console.print(f"[bold green]✓[/bold green] Extraction completed!")
        console.print()
        
        # Results summary
        console.print("[bold]Extraction Results:[/bold]")
        console.print(f"[cyan]• Documents processed:[/cyan] {result.total_documents_processed}")
        console.print(f"[cyan]• Documents with use cases:[/cyan] {result.documents_with_use_cases}")
        console.print(f"[cyan]• Total use cases found:[/cyan] {result.total_use_cases_found}")
        console.print(f"[cyan]• Final use cases (after deduplication):[/cyan] {len(result.final_use_cases)}")
        console.print(f"[cyan]• Processing time:[/cyan] {result.processing_time_seconds:.1f} seconds")
        
        if result.errors:
            console.print(f"[yellow]• Warnings/Errors:[/yellow] {len(result.errors)}")
            for error in result.errors[:3]:  # Show first 3 errors
                console.print(f"  [dim]- {error}[/dim]")
            if len(result.errors) > 3:
                console.print(f"  [dim]... and {len(result.errors) - 3} more[/dim]")
        
        console.print()
        
        if result.final_use_cases:
            console.print("[bold]Generated Use Cases:[/bold]")
            for i, use_case in enumerate(result.final_use_cases[:3], 1):  # Show first 3
                console.print(f"[green]{i}.[/green] [bold]{use_case.name}[/bold]")
                console.print(f"   [dim]{use_case.elevator_pitch}[/dim]")
                console.print(f"   [blue]Target:[/blue] {use_case.target_audience} | [blue]Level:[/blue] {use_case.complexity_level}")
                console.print()
            
            if len(result.final_use_cases) > 3:
                console.print(f"[dim]... and {len(result.final_use_cases) - 3} more use cases[/dim]")
                console.print()
        
        # Next steps
        console.print("[bold]Next Steps:[/bold]")
        if context.is_manual_agent():
            console.print(f"[yellow]•[/yellow] Use 'stackbench print-prompt {run_id} --use-case <n>' to see prompts for manual execution")
            console.print(f"[yellow]•[/yellow] Create solutions in the use case directories")
            console.print(f"[yellow]•[/yellow] Use 'stackbench analyze {run_id}' when done")
        else:
            console.print(f"[yellow]•[/yellow] Use 'stackbench execute {run_id} --agent <agent>' to run automated execution")
            console.print(f"[yellow]•[/yellow] Use 'stackbench analyze {run_id}' to generate analysis")
        
        console.print(f"[dim]•[/dim] Use 'stackbench status {run_id}' to check progress")
        
    except FileNotFoundError:
        console.print(f"[bold red]✗[/bold red] Run ID '{run_id}' not found.")
        console.print("[dim]Use 'stackbench list' to see available runs.[/dim]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[bold red]✗[/bold red] Failed to extract use cases: {e}")
        sys.exit(1)


@cli.command("print-prompt")
@click.argument("run_id")
@click.option("--use-case", "-u", type=int, required=True, help="Use case number (1-based)")
@click.option("--agent", "-a", default=None, help="Agent type override (default: use run config)")
@click.option("--copy", "-c", is_flag=True, help="Copy prompt to clipboard")
def print_prompt(run_id: str, use_case: int, agent: Optional[str], copy: bool):
    """Print formatted prompt for manual execution of a specific use case."""
    try:
        # Load run context
        context = RunContext.load(run_id)
        
        # Validate run phase
        if context.status.phase not in ["extracted", "executed", "analyzed"]:
            console.print(f"[bold red]✗[/bold red] Run must be extracted first, currently: {context.status.phase}")
            if context.status.phase == "cloned":
                console.print("[dim]Use 'stackbench extract <run-id>' first to generate use cases.[/dim]")
            sys.exit(1)
        
        # Determine agent to use
        agent_name = agent or context.config.agent_type
        
        # For now, only support cursor (can be extended later)
        if agent_name.lower() != "cursor":
            console.print(f"[bold red]✗[/bold red] Agent '{agent_name}' not supported yet. Currently supported: cursor")
            sys.exit(1)
        
        # Create agent and format prompt
        cursor_agent = CursorIDEAgent()
        
        try:
            prompt = cursor_agent.format_prompt(run_id, use_case)
        except ValueError as e:
            console.print(f"[bold red]✗[/bold red] {e}")
            sys.exit(1)
        
        # Display prompt with clear demarcation
        console.print(f"[bold blue]Use Case {use_case} Prompt for {agent_name.title()}:[/bold blue]")
        console.print()
        
        # Prompt start marker
        console.print("[bold cyan]╭─── PROMPT START ─────────────────────────────────────────────────────────────╮[/bold cyan]")
        console.print()
        
        # Clean prompt content (without rich formatting for clipboard)
        console.print(prompt)
        
        console.print()
        console.print("[bold cyan]╰─── PROMPT END ───────────────────────────────────────────────────────────────╯[/bold cyan]")
        
        # Handle clipboard copy if requested
        if copy:
            try:
                import pyperclip
                pyperclip.copy(prompt)
                console.print()
                console.print("[bold green]✓[/bold green] Prompt copied to clipboard!")
            except ImportError:
                console.print()
                console.print("[yellow]⚠[/yellow] pyperclip not available. Install with: uv add pyperclip")
            except Exception as e:
                console.print()
                console.print(f"[yellow]⚠[/yellow] Failed to copy to clipboard: {e}")
        
        # Show helpful next steps
        target_dir = cursor_agent.get_target_directory(run_id, use_case)
        try:
            relative_target_dir = target_dir.relative_to(Path.cwd())
        except ValueError:
            # If target_dir is not under current working directory, use absolute path
            relative_target_dir = target_dir
        
        console.print(f"\n[bold]Next Steps:[/bold]")
        if copy:
            console.print(f"[yellow]1.[/yellow] Paste the prompt from clipboard into Cursor IDE")
        else:
            console.print(f"[yellow]1.[/yellow] Copy the prompt above (or use --copy flag)")
        console.print(f"[yellow]2.[/yellow] Open Cursor IDE in the repository directory")
        console.print(f"[yellow]3.[/yellow] Create your solution in: [cyan]{relative_target_dir}/solution.py[/cyan]")
        console.print(f"[yellow]4.[/yellow] Use 'stackbench analyze {run_id}' when all use cases are complete")
        
    except FileNotFoundError:
        console.print(f"[bold red]✗[/bold red] Run ID '{run_id}' not found.")
        console.print("[dim]Use 'stackbench list' to see available runs.[/dim]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[bold red]✗[/bold red] Failed to generate prompt: {e}")
        sys.exit(1)


@cli.command("analyze")
@click.argument("run_id")
@click.option("--use-case", "-u", type=int, help="Analyze specific use case only (1-based)")
@click.option("--force", is_flag=True, help="Force re-analysis even if already completed")
@click.option("--workers", "-w", type=int, help="Number of parallel analysis workers (default: from config)")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed hook logs and debugging output")
def analyze(run_id: str, use_case: Optional[int], force: bool, workers: Optional[int], verbose: bool):
    """Analyze use case implementations using Claude Code."""
    import asyncio
    import json
    import os
    
    try:
        # Check for Anthropic API key (check both config and environment)
        config = get_config()
        anthropic_key = os.getenv("ANTHROPIC_API_KEY") or config.anthropic_api_key
        if not anthropic_key:
            console.print("[bold red]✗[/bold red] ANTHROPIC_API_KEY not found.")
            console.print("[dim]Add your Anthropic API key to .env file or environment.[/dim]")
            sys.exit(1)
        
        # Check if Node.js Claude Code CLI is installed
        import subprocess
        try:
            result = subprocess.run(["claude", "--version"], capture_output=True, text=True)
            if result.returncode != 0:
                raise FileNotFoundError
        except FileNotFoundError:
            console.print("[bold red]✗[/bold red] Claude Code CLI not found.")
            console.print("[dim]Install with: npm install -g @anthropic-ai/claude-code[/dim]")
            sys.exit(1)
        
        # Load run context
        try:
            context = RunContext.load(run_id)
        except FileNotFoundError:
            console.print(f"[bold red]✗[/bold red] Run ID '{run_id}' not found.")
            console.print("[dim]Use 'stackbench list' to see available runs.[/dim]")
            sys.exit(1)
        
        # Validate run phase
        if context.status.phase not in ["extracted", "executed", "analyzed"] and not force:
            console.print(f"[bold red]✗[/bold red] Run must be extracted first, currently: {context.status.phase}")
            if context.status.phase == "cloned":
                console.print("[dim]Use 'stackbench extract <run-id>' first to generate use cases.[/dim]")
            sys.exit(1)
        
        # Check if already analyzed and not forcing
        if context.status.phase == "analyzed" and not force:
            console.print(f"[yellow]⚠[/yellow] Run already analyzed. Use --force to re-analyze.")
            results_file = context.data_dir / "results.json"
            if results_file.exists():
                console.print(f"[dim]Results available at: {results_file}[/dim]")
            return
        
        show_logo()
        console.print(f"[bold blue]Analyzing Use Case Implementations[/bold blue]")
        console.print(f"Repository: [cyan]{context.config.repo_url}[/cyan]")
        console.print(f"Run ID: [dim]{run_id}[/dim]")
        console.print()
        
        # Create analyzer
        analyzer = ClaudeAnalyzer(verbose=verbose)
        
        if verbose:
            console.print("[dim]Running in verbose mode - detailed hook logs will be shown[/dim]")
        
        # Get worker count from config if not specified
        config = get_config()
        if workers is None:
            workers = config.analysis_max_workers
        
        if use_case:
            console.print(f"[yellow]Analyzing use case {use_case} only...[/yellow]")
            
            async def run_single_use_case_analysis():
                try:
                    result = await analyzer.analyze_single_use_case(run_id, use_case)
                    return result
                except Exception as e:
                    console.print(f"[bold red]✗[/bold red] Single use case analysis failed: {e}")
                    sys.exit(1)
            
            # Run single use case analysis
            result = asyncio.run(run_single_use_case_analysis())
            
            console.print()
            console.print("[bold green]✓[/bold green] Single use case analysis completed!")
            
            # Show result for single use case
            if "error" in result:
                console.print(f"[bold red]✗[/bold red] Analysis failed: {result['error']}")
            else:
                console.print(f"[bold]Use Case {use_case} Results:[/bold]")
                console.print(f"Name: [cyan]{result.get('use_case_name', 'Unknown')}[/cyan]")
                
                code_exec = result.get("code_executability", {})
                is_executable = code_exec.get("is_executable", False)
                status_color = "green" if is_executable else "red"
                console.print(f"Executable: [{status_color}]{is_executable}[/{status_color}]")
                
                if not is_executable:
                    failure_reason = code_exec.get("failure_reason", "Unknown")
                    console.print(f"Failure reason: [red]{failure_reason}[/red]")
                
                lib_usage = result.get("underlying_library_usage", {})
                was_used = lib_usage.get("was_used", False)
                was_mocked = lib_usage.get("was_mocked", False)
                console.print(f"Library used: [cyan]{was_used}[/cyan], Mocked: [cyan]{was_mocked}[/cyan]")
                
                quality = result.get("quality_assessment", {})
                overall_score = quality.get("overall_score", "N/A")
                console.print(f"Overall score: [cyan]{overall_score}[/cyan]")
            
            # Show result file location (already saved by analyzer)
            try:
                context = RunContext.load(run_id)
                use_case_dir = context.data_dir / f"use_case_{use_case}"
                result_file = use_case_dir / f"use_case_{use_case}_analysis.json"
                if result_file.exists():
                    console.print(f"• Analysis result saved: [cyan]{result_file}[/cyan]")
                else:
                    console.print(f"[yellow]Warning: Expected result file not found: {result_file}[/yellow]")
            except Exception as e:
                console.print(f"[yellow]Warning: Could not locate result file: {e}[/yellow]")
        else:
            # Validate workers count
            if workers < 1 or workers > 10:
                console.print("[bold red]✗[/bold red] Number of workers must be between 1 and 10")
                sys.exit(1)
            
            console.print(f"[yellow]Analyzing all use cases with {workers} parallel workers...[/yellow]")
            
            async def run_analysis():
                try:
                    result = await analyzer.analyze_run(run_id, max_workers=workers)
                    return result
                except Exception as e:
                    console.print(f"[bold red]✗[/bold red] Analysis failed: {e}")
                    sys.exit(1)
            
            # Run analysis
            result = asyncio.run(run_analysis())
            
            console.print()
            console.print("[bold green]✓[/bold green] Analysis completed successfully!")
            
            # Show simple summary since we're not generating overall results
            total_cases = len(result)
            successful_cases = sum(1 for r in result if r.get("code_executability", {}).get("is_executable") in [True, "partial"])
            
            console.print(f"[bold]Results Summary:[/bold]")
            console.print(f"Total Use Cases: [cyan]{total_cases}[/cyan]")
            console.print(f"Successful/Partial: [cyan]{successful_cases}[/cyan]")
            console.print(f"Success Rate: [cyan]{successful_cases/total_cases:.1%}[/cyan]" if total_cases > 0 else "")
            
            # Show individual use case results  
            console.print(f"[bold]Use Case Results:[/bold]")
            for use_case_result in result:
                use_case_num = use_case_result.get("use_case_number", "?")
                use_case_name = use_case_result.get("use_case_name", "Unknown")
                is_executable = use_case_result.get("code_executability", {}).get("is_executable", False)
                
                status_color = "green" if is_executable in [True, "partial"] else "red"
                status_text = "✓" if is_executable is True else "◐" if is_executable == "partial" else "✗"
                exec_text = "PASS" if is_executable is True else "PARTIAL" if is_executable == "partial" else "FAIL"
                
                console.print(f"• [{status_color}]{status_text}[/{status_color}] Use Case {use_case_num}: {use_case_name} - [{status_color}]{exec_text}[/{status_color}]")
            
            if context.status.phase != "analyzed":
                context.mark_analysis_completed()
                console.print(f"• Run status updated to: [green]analyzed[/green]")
    
    except KeyboardInterrupt:
        console.print("\n[yellow]Analysis interrupted by user.[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[bold red]✗[/bold red] Failed to analyze run: {e}")
        sys.exit(1)


def main():
    """Main entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()