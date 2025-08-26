"""Rich-based CLI for StackBench."""

import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional
import uuid
import click
from rich.console import Console
from rich.table import Table
import subprocess

from .config import get_config
from .core.repository import RepositoryManager
from .core.run_context import RunContext, RunPhase
from .extractors.extractor import extract_use_cases
from .agents.cursor_ide import CursorIDEAgent
from .analyzers.individual_analyzer import IndividualAnalyzer
from .analyzers.overall_analyzer import OverallAnalyzer

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


def get_phase_color(phase) -> str:
    """Get color for phase status."""
    # Handle both enum and string values
    phase_str = phase.value if hasattr(phase, 'value') else str(phase)
    
    color_map = {
        "created": "dim",
        "cloned": "blue", 
        "extracted": "yellow",
        "execution": "cyan",
        "analysis_individual": "green",
        "analysis_overall": "green",
        "completed": "bold green",
        "failed": "bold red"
    }
    return color_map.get(phase_str, "white")


def format_datetime(dt_str: str) -> str:
    """Format datetime string for display."""
    try:
        dt = datetime.fromisoformat(dt_str)
        return dt.strftime("%Y-%m-%d %H:%M")
    except:
        return dt_str


def show_help_with_logo(ctx, _, value):
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
    "--agent", "-a",
    default="cursor",
    help="Agent type (default: cursor)"
)
@click.option(
    "--branch", "-b",
    default="main",
    help="Git branch to clone (default: main)"
)
def clone(repo_url: str, include_folders: str, agent: str, branch: str):
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
            
            # Set the agent type in the context
            context.config.agent_type = agent
            context.save()
        
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


@cli.command()
@click.argument("repo_url")
@click.option(
    "--include-folders", "-i",
    default="", 
    help="Comma-separated list of folders to include (e.g., docs,examples,tests)"
)
@click.option(
    "--agent", "-a",
    default="cursor",
    help="Agent type for IDE execution (default: cursor)"
)
@click.option(
    "--branch", "-b",
    default="main",
    help="Git branch to clone (default: main)"
)
def setup(repo_url: str, include_folders: str, agent: str, branch: str):
    """Set up a new benchmark run for IDE agents (clone + extract + ready for manual execution)."""
    show_logo()
    console.print(f"[bold blue]Setting up IDE workflow for {agent.title()}[/bold blue]")
    console.print(f"Repository: [cyan]{repo_url}[/cyan]")
    if include_folders:
        console.print(f"Include folders: [dim]{include_folders}[/dim]")
    console.print()
    
    try:
        # Step 1: Clone repository
        with console.status("[bold green]Cloning repository..."):
            repo_manager = RepositoryManager()
            parsed_folders = parse_include_folders(include_folders)
            
            context = repo_manager.clone_repository(
                repo_url=repo_url,
                include_folders=parsed_folders,
                branch=branch
            )
            
            # Set the agent type in the context
            context.config.agent_type = agent
            context.save()
        
        console.print(f"[bold green]✓[/bold green] Repository cloned successfully!")
        console.print(f"[bold blue]Run ID:[/bold blue] {context.run_id}")
        console.print()
        
        # Step 2: Extract use cases
        with console.status("[bold green]Setting up DSPy and analyzing documents..."):
            try:
                result = extract_use_cases(context)
            except Exception as e:
                console.print(f"[bold red]✗[/bold red] Extraction failed: {e}")
                context.add_error(f"Extraction failed: {str(e)}")
                sys.exit(1)
        
        # Mark extraction as completed with use cases
        context.mark_extraction_completed(result.final_use_cases)
        
        console.print(f"[bold green]✓[/bold green] Use case extraction completed!")
        console.print()
        
        # Step 3: Show summary and first use case prompt
        console.print("[bold]Setup Summary:[/bold]")
        console.print(f"[cyan]• Run ID:[/cyan] {context.run_id}")
        console.print(f"[cyan]• Agent Type:[/cyan] {agent}")
        console.print(f"[cyan]• Repository:[/cyan] {context.repo_name}")
        console.print(f"[cyan]• Use Cases Generated:[/cyan] {len(result.final_use_cases)}")
        console.print()
        
        if result.final_use_cases:
            console.print("[bold]Generated Use Cases:[/bold]")
            for i, use_case in enumerate(result.final_use_cases[:3], 1):
                console.print(f"[green]{i}.[/green] [bold]{use_case.name}[/bold]")
                console.print(f"   [dim]{use_case.elevator_pitch}[/dim]")
            
            if len(result.final_use_cases) > 3:
                console.print(f"[dim]... and {len(result.final_use_cases) - 3} more use cases[/dim]")
            console.print()
        
        # Step 4: Next steps guidance
        console.print("[bold]Next Steps - IDE Manual Execution:[/bold]")
        console.print(f"[yellow]1.[/yellow] Open {agent.title()} IDE in the repository directory")
        console.print(f"[yellow]2.[/yellow] Get prompts: [cyan]stackbench print-prompt {context.run_id} --use-case 1[/cyan]")
        console.print(f"[yellow]3.[/yellow] Create solutions in the use case directories")
        console.print(f"[yellow]4.[/yellow] When done: [cyan]stackbench analyze {context.run_id}[/cyan]")
        console.print()
        console.print("[bold cyan]Ready for manual execution![/bold cyan]")
        
    except Exception as e:
        console.print(f"[bold red]✗[/bold red] Setup failed: {e}")
        sys.exit(1)


@cli.command()
@click.argument("repo_url")
@click.option(
    "--include-folders", "-i",
    default="", 
    help="Comma-separated list of folders to include (e.g., docs,examples,tests)"
)
@click.option(
    "--agent", "-a",
    required=True,
    help="CLI agent type for automated execution (e.g., openai, anthropic)"
)
@click.option(
    "--branch", "-b",
    default="main",
    help="Git branch to clone (default: main)"
)
def run(repo_url: str, include_folders: str, agent: str, branch: str):
    """Run full automated benchmark pipeline for CLI agents (clone + extract + execute + analyze)."""
    show_logo()
    console.print(f"[bold red]✗[/bold red] Automated CLI agents not yet implemented.")
    console.print()
    console.print("[bold]Coming Soon:[/bold] Full automation with CLI agents")
    console.print(f"[dim]• Target agent: {agent}[/dim]")
    console.print(f"[dim]• Repository: {repo_url}[/dim]")
    console.print()
    console.print("[bold]Alternative - Use IDE workflow:[/bold]")
    console.print(f"[cyan]stackbench setup {repo_url} -a cursor[/cyan]")
    console.print(f"[cyan]stackbench analyze <run-id>[/cyan]")


@cli.command()
@click.argument("run_id")
@click.option(
    "--agent", "-a",
    required=True,
    help="CLI agent type for automated execution (e.g., openai, anthropic)"
)
def execute(run_id: str, agent: str):
    """Execute use cases with specified CLI agent (not yet implemented)."""
    show_logo()
    console.print(f"[bold red]✗[/bold red] Automated CLI execution not yet implemented.")
    console.print()
    console.print("[bold]Coming Soon:[/bold] Automated use case execution")
    console.print(f"[dim]• Run ID: {run_id}[/dim]")
    console.print(f"[dim]• Target agent: {agent}[/dim]")
    console.print()
    console.print("[bold]Alternative - Use IDE workflow:[/bold]")
    console.print(f"[cyan]stackbench print-prompt {run_id} --use-case 1[/cyan]")
    console.print(f"[cyan]# Create solutions manually in IDE[/cyan]")
    console.print(f"[cyan]stackbench analyze {run_id}[/cyan]")


@cli.command()
@click.argument("run_id")
def status(run_id: str):
    """Show detailed status and progress for a benchmark run."""
    show_logo()
    try:
        context = RunContext.load(run_id)
        
        # For manual agents, detect any new implementations
        if context.is_manual_agent():
            newly_detected = context.detect_and_update_manual_implementations()
            if newly_detected:
                console.print(f"[green]Detected {len(newly_detected)} new implementations: {newly_detected}[/green]")
                console.print()
        
        # Header
        console.print(f"[bold blue]Run Status:[/bold blue] {context.run_id}")
        console.print(f"Repository: [cyan]{context.repo_name}[/cyan]")
        console.print(f"Agent Type: [cyan]{context.config.agent_type}[/cyan]")
        console.print()
        
        # Phase progress
        phase = context.status.phase
        phase_str = phase.value if hasattr(phase, 'value') else str(phase)
        phase_color = get_phase_color(phase)
        console.print(f"[bold]Current Phase:[/bold] [{phase_color}]{phase_str}[/{phase_color}]")
        
        # Phase timeline
        console.print("[bold]Phase Timeline:[/bold]")
        phases_info = [
            ("created", True),
            ("cloned", context.status.clone_completed),
            ("extracted", context.status.extraction_completed),
            ("execution", context.status.execution_phase_completed),
            ("analysis_individual", context.status.individual_analysis_completed),
            ("analysis_overall", context.status.overall_analysis_completed),
        ]
        
        for phase_name, completed in phases_info:
            if completed:
                console.print(f"  [green]✓[/green] {phase_name}")
            elif phase_name == phase_str:
                console.print(f"  [yellow]▶[/yellow] {phase_name} [dim](in progress)[/dim]")
            else:
                console.print(f"  [dim]○ {phase_name}[/dim]")
        
        console.print()
        
        # Use case progress
        if context.status.total_use_cases > 0:
            console.print("[bold]Use Case Progress:[/bold]")
            console.print(f"Total: [cyan]{context.status.total_use_cases}[/cyan]")
            console.print(f"Executed: [cyan]{context.status.executed_count}[/cyan]")
            console.print(f"Analyzed: [cyan]{context.status.analyzed_count}[/cyan]")
            console.print()
            
            # Individual use case status
            console.print("[bold]Individual Use Cases:[/bold]")
            for num, uc in context.status.use_cases.items():
                exec_status = "✓" if uc.is_executed else "○"
                exec_color = "green" if uc.is_executed else "dim"
                
                anal_status = "✓" if uc.is_analyzed else "○"
                anal_color = "green" if uc.is_analyzed else "dim"
                
                console.print(f"  [{exec_color}]{exec_status}[/{exec_color}] [{anal_color}]{anal_status}[/{anal_color}] Use Case {num}: [cyan]{uc.name}[/cyan]")
                
                if uc.execution_error:
                    console.print(f"     [red]Error: {uc.execution_error}[/red]")
                if uc.analysis_error:
                    console.print(f"     [red]Analysis Error: {uc.analysis_error}[/red]")
        
        console.print()
        
        # Errors
        if context.status.errors:
            console.print("[bold red]Errors:[/bold red]")
            for error in context.status.errors[-5:]:  # Show last 5 errors
                console.print(f"  [red]• {error}[/red]")
            if len(context.status.errors) > 5:
                console.print(f"  [dim]... and {len(context.status.errors) - 5} more errors[/dim]")
            console.print()
        
        # Next steps
        console.print("[bold]Suggested Next Steps:[/bold]")
        if phase_str == "cloned":
            console.print(f"[yellow]•[/yellow] Run: [cyan]stackbench extract {run_id}[/cyan]")
        elif phase_str == "extracted":
            if context.is_manual_agent():
                console.print(f"[yellow]•[/yellow] Get prompts: [cyan]stackbench print-prompt {run_id} --use-case 1[/cyan]")
                console.print(f"[yellow]•[/yellow] Create solutions manually in IDE")
                console.print(f"[yellow]•[/yellow] Analyze: [cyan]stackbench analyze {run_id}[/cyan]")
            else:
                console.print(f"[yellow]•[/yellow] Execute: [cyan]stackbench execute {run_id} --agent <agent>[/cyan]")
        elif phase_str == "execution":
            console.print(f"[yellow]•[/yellow] Analyze: [cyan]stackbench analyze {run_id}[/cyan]")
        elif phase_str == "analysis_individual":
            console.print(f"[yellow]•[/yellow] Generate overall report: [cyan]stackbench analyze {run_id}[/cyan]")
        elif phase_str == "completed":
            console.print("[green]•[/green] Benchmark complete! Check results.json and results.md")
        
    except FileNotFoundError:
        console.print(f"[bold red]✗[/bold red] Run ID '{run_id}' not found.")
        console.print("[dim]Use 'stackbench list' to see available runs.[/dim]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[bold red]✗[/bold red] Failed to get status: {e}")
        sys.exit(1)


@cli.command()
@click.option(
    "--older-than", "-o",
    type=int,
    default=30,
    help="Remove runs older than N days (default: 30)"
)
@click.option(
    "--dry-run", "-n",
    is_flag=True,
    help="Show what would be deleted without actually deleting"
)
@click.confirmation_option(
    prompt="Are you sure you want to delete old benchmark runs?"
)
def clean(older_than: int, dry_run: bool):
    """Clean up old benchmark runs."""
    import shutil
    from datetime import timedelta
    
    show_logo()
    console.print(f"[bold blue]Cleaning benchmark runs older than {older_than} days[/bold blue]")
    console.print()
    
    try:
        config = get_config()
        data_dir = config.data_dir
        
        if not data_dir.exists():
            console.print("[yellow]No data directory found - nothing to clean.[/yellow]")
            return
        
        # Find all valid run directories
        cutoff_date = datetime.now() - timedelta(days=older_than)
        runs_to_delete = []
        total_size = 0
        
        for item in data_dir.iterdir():
            if (item.is_dir() and 
                len(item.name) == 36 and  # UUID length
                (item / "run_context.json").exists()):
                try:
                    uuid.UUID(item.name)
                    
                    # Check creation time
                    context_file = item / "run_context.json"
                    creation_time = datetime.fromtimestamp(context_file.stat().st_mtime)
                    
                    if creation_time < cutoff_date:
                        # Calculate directory size
                        dir_size = sum(f.stat().st_size for f in item.rglob('*') if f.is_file())
                        total_size += dir_size
                        
                        # Load context for better info
                        try:
                            context = RunContext.load(item.name)
                            runs_to_delete.append((item, context, creation_time, dir_size))
                        except:
                            # If we can't load context, still include it for deletion
                            runs_to_delete.append((item, None, creation_time, dir_size))
                            
                except ValueError:
                    continue
        
        if not runs_to_delete:
            console.print(f"[green]No runs older than {older_than} days found.[/green]")
            return
        
        # Format size
        def format_size(size_bytes):
            if size_bytes < 1024:
                return f"{size_bytes} B"
            elif size_bytes < 1024 * 1024:
                return f"{size_bytes / 1024:.1f} KB"
            else:
                return f"{size_bytes / (1024 * 1024):.1f} MB"
        
        # Show what will be deleted
        console.print(f"[bold]Found {len(runs_to_delete)} runs to delete:[/bold]")
        console.print()
        
        for item, context, creation_time, dir_size in runs_to_delete:
            run_id = item.name[:8] + "..."  # Show first 8 chars
            repo_name = context.repo_name if context else "Unknown"
            age_days = (datetime.now() - creation_time).days
            
            console.print(f"• [dim]{run_id}[/dim] [cyan]{repo_name}[/cyan] "
                         f"[dim]({age_days} days old, {format_size(dir_size)})[/dim]")
        
        console.print()
        console.print(f"[bold]Total space to free:[/bold] {format_size(total_size)}")
        console.print()
        
        if dry_run:
            console.print("[yellow]Dry run - no files were deleted.[/yellow]")
            return
        
        # Delete runs
        deleted_count = 0
        for item, context, creation_time, dir_size in runs_to_delete:
            try:
                shutil.rmtree(item)
                deleted_count += 1
            except Exception as e:
                console.print(f"[red]Failed to delete {item.name}: {e}[/red]")
        
        console.print(f"[bold green]✓[/bold green] Deleted {deleted_count} benchmark runs")
        console.print(f"[green]Freed {format_size(total_size)} of disk space[/green]")
        
    except Exception as e:
        console.print(f"[bold red]✗[/bold red] Failed to clean runs: {e}")
        sys.exit(1)


@cli.command("list")
def list_runs():
    """List all benchmark runs with their status."""
    show_logo()
    try:
        # Get all run directories directly from data directory
        config = get_config()
        data_dir = config.data_dir
        
        if not data_dir.exists():
            console.print("[yellow]No benchmark runs found.[/yellow]")
            console.print("[dim]Use 'stackbench clone <repo-url>' to create a new run.[/dim]")
            return
            
        # Find all valid run directories (UUID-named with run_context.json)
        run_ids = []
        for item in data_dir.iterdir():
            if (item.is_dir() and 
                len(item.name) == 36 and  # UUID length
                (item / "run_context.json").exists()):
                try:
                    uuid.UUID(item.name)
                    run_ids.append(item.name)
                except ValueError:
                    continue
        
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
                
                # For manual agents, detect any new implementations
                if context.is_manual_agent():
                    context.detect_and_update_manual_implementations()
                
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
            phase = summary["phase"]
            phase_str = phase.value if hasattr(phase, 'value') else str(phase)
            phase_colored = f"[{get_phase_color(phase)}]{phase_str}[/{get_phase_color(phase)}]"
            
            # Status column - show progress within current phase or what's needed next
            status_parts = []
            
            # Show errors if any
            if summary["has_errors"]:
                status_parts.append("[red]⚠ errors[/red]")
            
            phase_val = context.status.phase.value
            total = summary["total_use_cases"]
            executed = summary["executed_use_cases"] 
            analyzed = context.status.analyzed_count
            
            # Determine status based on current phase and progress
            if phase_val == "created":
                status_parts.append("[dim]ready for clone[/dim]")
            elif phase_val == "cloned":
                status_parts.append("[blue]ready for extraction[/blue]")
            elif phase_val == "extracted":
                # Extraction completed - show execution progress or readiness
                if total > 0:
                    if executed == 0:
                        status_parts.append("[yellow]ready for execution[/yellow]")
                    elif executed < total:
                        status_parts.append(f"[cyan]{executed}/{total} executed[/cyan]")
                    else:
                        # This shouldn't happen in this phase, but handle gracefully
                        status_parts.append("[green]execution complete[/green]")
                else:
                    status_parts.append("[yellow]ready for execution[/yellow]")
            elif phase_val == "execution":
                # Execution completed - show analysis progress or readiness
                if total > 0:
                    if analyzed == 0:
                        status_parts.append("[yellow]ready for analysis[/yellow]")
                    elif analyzed < executed:  # Only analyze executed use cases
                        status_parts.append(f"[magenta]{analyzed}/{executed} analyzed[/magenta]")
                    else:
                        status_parts.append("[green]analysis complete[/green]")
                else:
                    status_parts.append("[yellow]ready for analysis[/yellow]")
            elif phase_val == "analysis_individual":
                # Individual analysis completed - show overall analysis readiness
                status_parts.append("[yellow]ready for overall analysis[/yellow]")
            elif phase_val == "analysis_overall":
                # Overall analysis completed
                status_parts.append("[green]overall analysis complete[/green]")
            elif phase_val == "completed":
                status_parts.append("[green]completed[/green]")
            
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
        if context.status.phase != RunPhase.CLONED:
            console.print(f"[bold red]✗[/bold red] Run must be in 'cloned' phase, currently: {context.status.phase}")
            if context.status.phase == RunPhase.CREATED:
                console.print("[dim]Use 'stackbench clone <repo-url>' first to clone the repository.[/dim]")
            elif context.status.phase == RunPhase.EXTRACTED:
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
        
        # Mark extraction as completed with use cases
        context.mark_extraction_completed(result.final_use_cases)
        
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
        valid_phases = [RunPhase.EXTRACTED, RunPhase.EXECUTION, RunPhase.ANALYSIS_INDIVIDUAL, RunPhase.ANALYSIS_OVERALL, RunPhase.COMPLETED]
        if context.status.phase not in valid_phases:
            console.print(f"[bold red]✗[/bold red] Run must be extracted first, currently: {context.status.phase}")
            if context.status.phase == RunPhase.CLONED:
                console.print("[dim]Use 'stackbench extract <run-id>' first to generate use cases.[/dim]")
            sys.exit(1)
        
        # For manual agents, detect any new implementations
        if context.is_manual_agent():
            context.detect_and_update_manual_implementations()
        
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
@click.option("--skip-overall", is_flag=True, help="Skip overall analysis report generation")
def analyze(run_id: str, use_case: Optional[int], force: bool, workers: Optional[int], verbose: bool, skip_overall: bool):
    """Analyze use case implementations using Claude Code."""
    import asyncio
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
        
        # Validate run phase for individual analysis
        # EXTRACTED: extraction complete, may have some executions to analyze
        # EXECUTION: execution complete, ready for individual analysis  
        # ANALYSIS_INDIVIDUAL: individual analysis complete, can do overall analysis
        valid_phases = [RunPhase.EXTRACTED, RunPhase.EXECUTION, RunPhase.ANALYSIS_INDIVIDUAL, RunPhase.ANALYSIS_OVERALL, RunPhase.COMPLETED]
        if context.status.phase not in valid_phases and not force:
            console.print(f"[bold red]✗[/bold red] Run must be extracted first, currently: {context.status.phase}")
            if context.status.phase == RunPhase.CLONED:
                console.print("[dim]Use 'stackbench extract <run-id>' first to generate use cases.[/dim]")
            elif context.status.phase == RunPhase.CREATED:
                console.print("[dim]Use 'stackbench clone <repo-url>' first to clone the repository.[/dim]")
            sys.exit(1)
        
        # For manual agents, detect any new implementations
        if context.is_manual_agent():
            newly_detected = context.detect_and_update_manual_implementations()
            if newly_detected:
                console.print(f"[green]Detected {len(newly_detected)} new implementations: {newly_detected}[/green]")
        
        # Check if individual analysis is already completed and handle accordingly
        if context.status.phase in [RunPhase.ANALYSIS_INDIVIDUAL, RunPhase.ANALYSIS_OVERALL, RunPhase.COMPLETED] and not force:
            console.print(f"[yellow]⚠[/yellow] Individual analysis already completed (phase: {context.status.phase}). Use --force to re-analyze.")
            
            # If already at ANALYSIS_INDIVIDUAL but user wants to run overall analysis
            if context.status.phase == RunPhase.ANALYSIS_INDIVIDUAL and not skip_overall:
                console.print("[bold blue]Individual analysis completed, proceeding to overall analysis...[/bold blue]")
                
                try:
                    # Create overall analyzer  
                    overall_analyzer = OverallAnalyzer(verbose=verbose)
                    
                    with console.status("[bold green]Generating results.json and results.md..."):
                        async def run_overall_analysis():
                            try:
                                result_paths = await overall_analyzer.analyze_run(run_id)
                                return result_paths
                            except Exception as e:
                                console.print(f"[bold red]✗[/bold red] Overall analysis failed: {e}")
                                return None
                        
                        # Run overall analysis
                        import asyncio
                        result_paths = asyncio.run(run_overall_analysis())
                        
                        if result_paths:
                            console.print("[bold green]✓[/bold green] Overall analysis completed successfully!")
                            
                            # Mark overall analysis as completed and update phase
                            context.status.overall_analysis_completed = True
                            context.status.update_phase_automatically()
                            context.save()
                            
                            console.print()
                            console.print("[bold]Generated Files:[/bold]")
                            console.print(f"• [cyan]results.json[/cyan]: {result_paths['results_json']}")
                            console.print(f"• [cyan]results.md[/cyan]: {result_paths['results_markdown']}")
                except Exception as e:
                    console.print(f"[bold red]✗[/bold red] Failed to run overall analysis: {e}")
            
            return
        
        # Check if there are any implementations to analyze
        if context.status.phase == RunPhase.EXTRACTED:
            # For EXTRACTED phase, we need implementations before we can analyze
            if context.status.executed_count == 0:
                console.print(f"[yellow]⚠[/yellow] No implementations found to analyze.")
                if context.is_manual_agent():
                    console.print("[dim]Create implementations first using 'stackbench print-prompt <run-id> --use-case <n>'[/dim]")
                else:
                    console.print("[dim]Execute use cases first before analysis.[/dim]")
                return
        
        show_logo()
        console.print(f"[bold blue]Analyzing Use Case Implementations[/bold blue]")
        console.print(f"Repository: [cyan]{context.config.repo_url}[/cyan]")
        console.print(f"Run ID: [dim]{run_id}[/dim]")
        console.print()
        
        # Create analyzer
        analyzer = IndividualAnalyzer(verbose=verbose)
        
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
            
            # Mark individual analysis as completed - this will update the phase to ANALYSIS_INDIVIDUAL
            if not context.status.individual_analysis_completed:
                context.mark_individual_analysis_completed()
                console.print(f"• Individual analysis status updated to: [green]completed[/green]")
                console.print(f"• Phase updated to: [green]{context.status.phase}[/green]")
            
            # Run overall analysis if not skipped and individual analysis is complete
            if not skip_overall and not use_case:  # Only run overall analysis for full runs, not single use case
                console.print()
                console.print("[bold blue]Generating Overall Analysis Report...[/bold blue]")
                
                try:
                    # Create overall analyzer
                    overall_analyzer = OverallAnalyzer(verbose=verbose)
                    
                    with console.status("[bold green]Generating results.json and results.md..."):
                        async def run_overall_analysis():
                            try:
                                result_paths = await overall_analyzer.analyze_run(run_id)
                                return result_paths
                            except Exception as e:
                                console.print(f"[bold red]✗[/bold red] Overall analysis failed: {e}")
                                return None
                        
                        # Run overall analysis
                        result_paths = asyncio.run(run_overall_analysis())
                        
                        if result_paths:
                            console.print("[bold green]✓[/bold green] Overall analysis completed successfully!")
                            
                            # Mark overall analysis as completed and update phase
                            context.status.overall_analysis_completed = True
                            context.status.update_phase_automatically()
                            context.save()
                            
                            console.print()
                            console.print("[bold]Generated Files:[/bold]")
                            console.print(f"• [cyan]results.json[/cyan]: {result_paths['results_json']}")
                            console.print(f"• [cyan]results.md[/cyan]: {result_paths['results_markdown']}")
                            console.print()
                            console.print("[bold]Analysis Summary:[/bold]")
                            
                            # Load and show key metrics from results.json
                            try:
                                import json
                                with open(result_paths['results_json'], 'r') as f:
                                    results_data = json.load(f)
                                
                                summary = results_data['overall_summary']
                                pass_fail = summary['pass_fail_status']
                                success_rate = summary['success_rate']
                                successful_cases = summary['successful_cases']
                                total_cases = summary['total_use_cases']
                                
                                status_color = "green" if pass_fail == "PASS" else "red"
                                console.print(f"• Status: [{status_color}]{pass_fail}[/{status_color}]")
                                console.print(f"• Success Rate: [cyan]{success_rate:.1f}%[/cyan] ({successful_cases}/{total_cases} use cases)")
                                
                            except Exception as e:
                                console.print(f"[yellow]Warning: Could not load results summary: {e}[/yellow]")
                        else:
                            console.print("[yellow]⚠[/yellow] Overall analysis failed, but individual analysis results are available.")
                            
                except Exception as e:
                    console.print(f"[bold red]✗[/bold red] Failed to run overall analysis: {e}")
                    console.print("[yellow]Individual analysis results are still available.[/yellow]")
    
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