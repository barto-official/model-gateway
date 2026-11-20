"""Minimal Typer application for docs and CLI reference generation."""

from __future__ import annotations

import typer

app = typer.Typer(
    help="Print a short acknowledgement (smoke-test friendly).",
    no_args_is_help=True,
    add_completion=True,
)


@app.callback()
def main() -> None:
    """Print a short acknowledgement (smoke-test friendly)."""
