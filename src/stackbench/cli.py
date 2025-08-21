"""Rich-based CLI for StackBench."""

import sys
from typing import List, Optional

import click
from rich.console import Console

from .core.repository import RepositoryManager

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


@click.group()
@click.version_option()
def cli():
    """StackBench - Open source local deployment tool for benchmarking coding agents."""
    pass


@cli.command()
@click.argument("repo_url")
@click.option(
    "--include-folders", "-i",
    default="", 
    help="Comma-separated list of folders to include (e.g., docs,examples,tests)"
)
def clone(repo_url: str, include_folders: str):
    """Clone a repository and set up a new benchmark run."""
    show_logo()
    try:
        with console.status("[bold green]Cloning repository..."):
            repo_manager = RepositoryManager()
            parsed_folders = parse_include_folders(include_folders)
            
            context = repo_manager.clone_repository(
                repo_url=repo_url,
                include_folders=parsed_folders
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


def main():
    """Main entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()