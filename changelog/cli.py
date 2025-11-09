"""Command-line interface for PR changelog tool."""

import argparse
import sys
from pathlib import Path

from rich.console import Console
from rich.markdown import Markdown

from .config import Config
from .github_client import GitHubClient
from .formatter import ChangelogFormatter
from .categorizer import PRCategorizer


def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        description="Generate changelogs from GitHub pull requests across multiple repositories"
    )
    parser.add_argument(
        "-c", "--config",
        type=Path,
        default=Path("config.yaml"),
        help="Path to configuration file (default: config.yaml)"
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        help="Write changelog to file instead of stdout"
    )
    parser.add_argument(
        "--plain",
        action="store_true",
        help="Output plain text instead of rich formatted markdown"
    )

    args = parser.parse_args()

    # Check if config file exists
    if not args.config.exists():
        print(f"Error: Configuration file not found: {args.config}", file=sys.stderr)
        print(f"\nCreate a config.yaml file (see config.example.yaml for reference)", file=sys.stderr)
        sys.exit(1)

    try:
        # Load configuration
        config = Config.from_file(args.config)

        # Fetch PRs from GitHub
        console = Console()
        with console.status("[bold green]Fetching pull requests from GitHub..."):
            client = GitHubClient(config)
            prs = client.fetch_pull_requests()
            client.close()

        if not prs:
            console.print("[yellow]No pull requests found matching the criteria.[/yellow]")
            return

        # Categorize PRs using Claude
        with console.status(f"[bold blue]Categorizing {len(prs)} PRs using Claude AI..."):
            categorizer = PRCategorizer(config)
            categorization = categorizer.categorize_batch(prs)
            categorizer.close()

        # Format changelog
        formatter = ChangelogFormatter(config)
        changelog = formatter.format(prs, categorization)

        # Output changelog
        if args.output:
            args.output.write_text(changelog)
            console.print(f"[green]✓[/green] Changelog written to {args.output}")
        elif args.plain:
            print(changelog)
        else:
            # Rich formatted output
            console.print(Markdown(changelog))

    except FileNotFoundError as e:
        error_console = Console(stderr=True)
        error_console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)
    except Exception as e:
        error_console = Console(stderr=True)
        error_console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
