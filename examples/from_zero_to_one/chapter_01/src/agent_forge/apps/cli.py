"""CLI entry for chapter 01."""

from __future__ import annotations

import typer

app = typer.Typer(help="agent_forge chapter 01 CLI")


@app.callback()
def main() -> None:
    """CLI root command group."""


@app.command()
def version() -> None:
    """Print chapter bootstrap version."""

    typer.echo("agent-forge-chapter-01")


if __name__ == "__main__":
    app()
