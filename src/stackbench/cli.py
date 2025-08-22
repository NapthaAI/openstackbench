"""Rich-based CLI for StackBench."""

import sys
from datetime import datetime
from typing import List, Optional

import click
from rich.console import Console
from rich.table import Table

from .core.repository import RepositoryManager
from .core.run_context import RunContext
from .extractors.extractor import extract_use_cases

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


def main():
    """Main entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()