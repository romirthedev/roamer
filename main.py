#!/usr/bin/env python3
"""Vercept — GUI-first AI agent for macOS computer control."""

import signal
import sys

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from config import load_config
from vercept.agent import Agent

console = Console()

# Track if we're mid-task for the double-Ctrl+C pattern
_running = False


def _handle_sigint(signum, frame):
    global _running
    if _running:
        console.print("\n[yellow]Stopping current task... (Ctrl+C again to quit)[/yellow]")
        _running = False
        raise KeyboardInterrupt
    else:
        console.print("\n[dim]Goodbye.[/dim]")
        sys.exit(0)


def main():
    global _running
    signal.signal(signal.SIGINT, _handle_sigint)

    console.print()
    console.print(
        Panel(
            "[bold white]Vercept[/bold white]\n"
            "[dim]GUI-first AI agent — sees your screen, takes actions.[/dim]\n"
            "[dim]Type an instruction, or 'quit' to exit.[/dim]\n"
            "[dim]Ctrl+C to stop a running task.[/dim]",
            border_style="cyan",
            padding=(1, 2),
        )
    )

    try:
        config = load_config()
    except SystemExit as e:
        console.print(f"[red]{e}[/red]")
        return

    if config.dry_run:
        console.print("[yellow]Dry-run mode: actions will be logged but not executed.[/yellow]")

    agent = Agent(config)

    while True:
        console.print()
        try:
            instruction = Prompt.ask("[bold cyan]vercept[/bold cyan]")
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Goodbye.[/dim]")
            break

        instruction = instruction.strip()
        if not instruction:
            continue
        if instruction.lower() in ("quit", "exit", "q"):
            console.print("[dim]Goodbye.[/dim]")
            break

        _running = True
        try:
            agent.run(instruction)
        except KeyboardInterrupt:
            console.print("[yellow]Task interrupted.[/yellow]")
        finally:
            _running = False


if __name__ == "__main__":
    main()
