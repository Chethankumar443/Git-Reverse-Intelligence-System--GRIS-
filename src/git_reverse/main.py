"""
Git Reverse CLI entry point.

Exposes:
  git-reverse              → Launch the TUI
  git-reverse analyze URL  → Run analysis in headless mode (CI-friendly)
  git-reverse doctor       → Environment health check
  git-reverse config       → View / set configuration values
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import click

from git_reverse import __version__
from git_reverse.config.settings import get_settings
from git_reverse.core.logging import configure_logging, get_logger

log = get_logger(__name__)


def _bootstrap() -> None:
    """One-time initialisation before any command runs."""
    settings = get_settings()
    configure_logging(settings.log_level, dev_mode=settings.dev_mode)


def print_exit_banner(session_id: str, timestamp: str) -> None:
    banner = r"""
    ██████╗ ██╗████████╗      ██████╗ ███████╗██╗   ██╗███████╗██████╗ ███████╗███████╗
   ██╔════╝ ██║╚══██╔══╝      ██╔══██╗██╔════╝██║   ██║██╔════╝██╔══██╗██╔════╝██╔════╝
   ██║  ███╗██║    ██║          ██████╔╝█████╗  ██║   ██║ █████╗  ██████╔╝███████╗█████╗
   ██║   ██║██║    ██║          ██╔══██╗██╔══╝  ╚██╗ ██╔╝██╔══╝   ██╔══██╗╚════██║██╔══╝
   ╚██████╔╝██║   ██║          ██║  ██║███████╗ ╚████╔╝ ███████╗ ██║  ██║███████║███████╗
    ╚═════╝ ╚═╝   ╚═╝          ╚═╝  ╚═╝╚══════╝  ╚═══╝  ╚══════╝  ╚═╝  ╚═╝╚══════╝╚══════╝
"""
    print(banner)
    print(f"  Session   New session - {timestamp}")
    print(f"  Continue  Git-Reverse - {session_id}")
    print()


class GitReverseGroup(click.Group):
    """Custom click Group that dynamically defaults to the 'tui' command for unknown args."""

    def parse_args(self, ctx: click.Context, args: list[str]) -> list[str]:
        if args:
            first = args[0]
            # If the first argument is not a known subcommand and doesn't start with a flag
            if not first.startswith("-") and first not in self.list_commands(ctx):
                args.insert(0, "tui")
        return super().parse_args(ctx, args)


# ── Root Group ────────────────────────────────────────────────────────────────
@click.group(
    cls=GitReverseGroup,
    invoke_without_command=True,
    context_settings={"help_option_names": ["-h", "--help"]},
)
@click.version_option(__version__, "-V", "--version", prog_name="git-reverse")
@click.pass_context
def cli(ctx: click.Context) -> None:
    """
    Git Reverse — Repository Intelligence Platform.

    Run without arguments to launch the interactive TUI.
    """
    _bootstrap()
    if ctx.invoked_subcommand is None:
        ctx.invoke(tui, session_id=None)


# ── TUI Command ───────────────────────────────────────────────────────────────
@cli.command("tui")
@click.argument("session_id", required=False, default=None)
def tui(session_id: str | None) -> None:
    """Launch the interactive terminal UI (default)."""
    import time

    from git_reverse.storage.database import Database
    from git_reverse.tui.app import GitReverseApp

    settings = get_settings()
    app = None

    async def _run() -> None:
        nonlocal app
        async with Database(settings.db_path) as db:
            app = GitReverseApp(settings=settings, db=db, initial_session_id=session_id)
            await app.run_async()

    try:
        asyncio.run(_run())
    except KeyboardInterrupt:
        pass
    finally:
        if app and app.active_session_id:
            timestamp = time.strftime('%Y-%m-%dT%H:%M:%S.000Z', time.gmtime())
            print_exit_banner(app.active_session_id, timestamp)


# ── Analyze Command (headless) ────────────────────────────────────────────────
@cli.command("analyze")
@click.argument("url_or_path")
@click.option("--mode", default="explore", show_default=True, help="Analysis mode.")
@click.option("--model", default=None, help="Override the default LLM model.")
@click.option("--output", type=click.Path(), default=None, help="Write results to this file.")
@click.option("--force", is_flag=True, default=False, help="Force re-clone even if cached.")
def analyze(
    url_or_path: str,
    mode: str,
    model: str | None,
    output: str | None,
    force: bool,
) -> None:
    """
    Analyze a repository in headless (non-TUI) mode.

    Useful for CI pipelines, scripting, or exporting documentation.

    \b
    Examples:
      git-reverse analyze https://github.com/tiangolo/fastapi
      git-reverse analyze ./my-local-project --mode architecture
    """
    import uuid

    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, TextColumn

    from git_reverse.ingestion.cloner import RepositoryCloner
    from git_reverse.ingestion.validator import RepositoryValidator
    from git_reverse.storage.database import Database, RepositoryDAO

    settings = get_settings()
    console = Console()

    async def _run_headless() -> None:
        async with Database(settings.db_path) as db:
            repo_dao = RepositoryDAO(db)
            cloner = RepositoryCloner(
                cache_dir=settings.repos_cache_path,
                timeout_seconds=settings.clone_timeout_seconds,
            )
            validator = RepositoryValidator(max_repo_size_mb=settings.max_repo_size_mb)

            # Register repo in DB
            from git_reverse.storage.database import Repository
            repo_id = str(uuid.uuid4())
            name = url_or_path.rstrip("/").split("/")[-1].replace(".git", "")
            await repo_dao.upsert(
                Repository(id=repo_id, url=url_or_path, name=name, analysis_status="running")
            )

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                # Clone
                task = progress.add_task("Cloning repository…", total=None)
                local_path = await cloner.clone(
                    url_or_path, repo_id=repo_id, force_reclone=force
                )
                progress.update(task, description="✓ Clone complete", completed=1, total=1)

                # Validate
                task2 = progress.add_task("Validating repository…", total=None)
                result = validator.validate(local_path)
                progress.update(task2, description="✓ Validation complete", completed=1, total=1)

                # Run AST Analysis Pipeline
                task3 = progress.add_task("Analyzing codebase AST & Dependency Graph…", total=None)
                from git_reverse.analysis.pipeline import AnalysisPipeline
                pipeline = AnalysisPipeline(db=db, max_workers=settings.effective_workers)
                await pipeline.run(repo_id=repo_id, validation_result=result)
                progress.update(task3, description="✓ Analysis complete", completed=1, total=1)

            # Get node/edge count from DB
            async with db.conn.execute("SELECT COUNT(*) FROM nodes WHERE repo_id = ?", (repo_id,)) as cursor:
                node_cnt_row = await cursor.fetchone()
            node_cnt = node_cnt_row[0] if node_cnt_row else 0

            async with db.conn.execute("SELECT COUNT(*) FROM edges WHERE source_id IN (SELECT id FROM nodes WHERE repo_id = ?)", (repo_id,)) as cursor:
                edge_cnt_row = await cursor.fetchone()
            edge_cnt = edge_cnt_row[0] if edge_cnt_row else 0

            # Print summary
            console.print(f"\n[bold green]Repository:[/] {name}")
            console.print(f"[bold]Branch:[/] {result.active_branch or 'detached HEAD'}")
            console.print(f"[bold]HEAD:[/] {result.head_sha[:12]}")
            console.print(f"[bold]Source files:[/] {len(result.manifest.source_files)}")
            console.print(f"[bold]Size:[/] {result.manifest.total_size_mb:.1f} MB")
            console.print(f"[bold]AST Nodes parsed:[/] {node_cnt}")
            console.print(f"[bold]Dependency edges:[/] {edge_cnt}")

            if output:
                import json
                out = {
                    "repo": name,
                    "url": url_or_path,
                    "head": result.head_sha,
                    "branch": result.active_branch,
                    "source_files": len(result.manifest.source_files),
                    "size_mb": result.manifest.total_size_mb,
                    "ast_nodes": node_cnt,
                    "dependency_edges": edge_cnt,
                }
                Path(output).write_text(json.dumps(out, indent=2))
                console.print(f"\n[dim]Results written to {output}[/]")

            await repo_dao.update_status(repo_id, "complete")

    try:
        asyncio.run(_run_headless())
    except Exception as exc:
        click.secho(f"Error: {exc}", fg="red", err=True)
        sys.exit(1)


# ── Doctor Command ────────────────────────────────────────────────────────────
@cli.command("doctor")
def doctor() -> None:
    """
    Run an environment health check.

    Verifies Git, Python version, API key presence, data directories,
    and disk space. Reports any issues with suggested fixes.
    """
    import shutil

    from rich.console import Console
    from rich.table import Table

    settings = get_settings()
    console = Console()
    table = Table(title="Git Reverse — Health Check", show_header=True)
    table.add_column("Check", style="bold")
    table.add_column("Status")
    table.add_column("Detail")

    def ok(label: str, detail: str = "") -> None:
        table.add_row(label, "[green]OK[/]", detail)

    def warn(label: str, detail: str = "") -> None:
        table.add_row(label, "[yellow]WARN[/]", detail)

    def fail(label: str, detail: str = "") -> None:
        table.add_row(label, "[red]FAIL[/]", detail)

    # Python version
    major, minor = sys.version_info[:2]
    if (major, minor) >= (3, 12):
        ok("Python version", f"{major}.{minor}")
    else:
        warn("Python version", f"{major}.{minor} (3.12+ recommended)")

    # Git binary
    git_path = shutil.which("git")
    if git_path:
        ok("Git binary", git_path)
    else:
        fail("Git binary", "git not found on PATH")

    # Data directory
    if settings.data_dir.exists():
        ok("Data directory", str(settings.data_dir))
    else:
        fail("Data directory", f"Missing: {settings.data_dir}")

    # Cache directory
    if settings.cache_dir.exists():
        ok("Cache directory", str(settings.cache_dir))
    else:
        warn("Cache directory", f"Missing: {settings.cache_dir}")

    # Database file
    if settings.db_path.exists():
        size_kb = settings.db_path.stat().st_size // 1024
        ok("Database", f"{settings.db_path.name} ({size_kb} KB)")
    else:
        ok("Database", "Will be created on first run")

    # OpenRouter API key
    if settings.has_openrouter_key():
        ok("OpenRouter API key", "Found (keychain or env)")
    else:
        warn("OpenRouter API key", "Not configured — run /settings or set OPENROUTER_API_KEY")

    # Disk space
    _total, _used, free = shutil.disk_usage(settings.data_dir)
    free_gb = free / (1024 ** 3)
    if free_gb >= 5:
        ok("Disk space", f"{free_gb:.1f} GB free")
    elif free_gb >= 1:
        warn("Disk space", f"{free_gb:.1f} GB free — low for large repos")
    else:
        fail("Disk space", f"{free_gb:.1f} GB free — critically low")

    console.print(table)


# ── Config Command ────────────────────────────────────────────────────────────
@cli.command("config")
@click.option("--set-key", "openrouter_key", default=None, metavar="KEY",
              help="Store an OpenRouter API key in the OS keychain.")
@click.option("--set-github-token", "github_token", default=None, metavar="TOKEN",
              help="Store a GitHub API token in the OS keychain.")
@click.option("--show", is_flag=True, default=False, help="Print current config (no secrets).")
def config(openrouter_key: str | None, github_token: str | None, show: bool) -> None:
    """View or update configuration values."""
    from rich.console import Console
    from rich.table import Table

    settings = get_settings()
    console = Console()

    if openrouter_key:
        settings.save_openrouter_key(openrouter_key)
        console.print("[green]✓ OpenRouter API key stored securely in OS keychain.[/]")

    if github_token:
        settings.save_github_token(github_token)
        console.print("[green]✓ GitHub token stored securely in OS keychain.[/]")

    if show or (not openrouter_key and not github_token):
        table = Table(title="Current Configuration")
        table.add_column("Setting")
        table.add_column("Value")
        table.add_row("Data directory", str(settings.data_dir))
        table.add_row("Cache directory", str(settings.cache_dir))
        table.add_row("Database", str(settings.db_path))
        table.add_row("Default model", settings.default_model)
        table.add_row("Analysis workers", str(settings.effective_workers))
        table.add_row("Clone timeout", f"{settings.clone_timeout_seconds}s")
        table.add_row("Max repo size", f"{settings.max_repo_size_mb} MB")
        table.add_row("Log level", settings.log_level)
        table.add_row("Dev mode", str(settings.dev_mode))
        table.add_row("OpenRouter key", "✓ configured" if settings.has_openrouter_key() else "✗ not set")
        console.print(table)


if __name__ == "__main__":
    cli()
