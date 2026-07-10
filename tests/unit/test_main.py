"""Tests for git-reverse CLI entrypoint."""

from __future__ import annotations

from click.testing import CliRunner

from git_reverse.main import cli


def test_cli_version() -> None:
    """Verify cli returns the version."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "git-reverse" in result.output


def test_cli_doctor() -> None:
    """Verify the doctor subcommand runs correctly and checks the environment."""
    runner = CliRunner()
    result = runner.invoke(cli, ["doctor"])
    assert result.exit_code == 0
    assert "Health Check" in result.output

