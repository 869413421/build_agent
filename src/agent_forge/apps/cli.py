"""CLI entry for agent-forge."""

from __future__ import annotations

import typer

app = typer.Typer(help="agent_forge CLI")


@app.callback()
def main() -> None:
    """CLI root command group."""


@app.command()
def health() -> None:
    """Simple CLI health check."""

    typer.echo("ok")


@app.command()
def version() -> None:
    """Print framework version."""

    typer.echo("agent-forge 0.1.0")


if __name__ == "__main__":
    app()

