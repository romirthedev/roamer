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

HELP_TEXT = """\
[bold]Commands:[/bold]
  [cyan]<instruction>[/cyan]         Run a task (e.g. "Open Safari and go to apple.com")
  [cyan]resume <task-id>[/cyan]      Resume a previous task by ID
  [cyan]sessions[/cyan]              List recent saved sessions
  [cyan]dry[/cyan]                   Toggle dry-run mode (log actions without executing)
  [cyan]help[/cyan]                  Show this help
  [cyan]quit[/cyan] / [cyan]exit[/cyan]           Exit

[bold]Tips:[/bold]
  • Press [bold]Ctrl+C[/bold] while a task is running to stop it gracefully.
  • Tasks are auto-saved — use [cyan]sessions[/cyan] to see them and [cyan]resume[/cyan] to continue.
  • Move the mouse to a screen corner to trigger the pyautogui failsafe (emergency stop).\
"""

# Track if we're mid-task for the double-Ctrl+C pattern
_running = False


def _handle_sigint(signum, frame):
    global _running
    if _running:
        console.print(
            "\n[yellow]Stopping current task... (Ctrl+C again to quit)[/yellow]"
        )
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
            "[dim]Type an instruction, 'help' for commands, or 'quit' to exit.[/dim]\n"
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
        console.print(
            "[yellow]Dry-run mode: actions will be logged but not executed.[/yellow]"
        )

    agent = Agent(config)

    while True:
        console.print()
        try:
            raw = Prompt.ask("[bold cyan]vercept[/bold cyan]")
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Goodbye.[/dim]")
            break

        raw = raw.strip()
        if not raw:
            continue

        lower = raw.lower()

        # ── Built-in commands ───────────────────────────────────────────

        if lower in ("quit", "exit", "q"):
            console.print("[dim]Goodbye.[/dim]")
            break

        if lower == "help":
            console.print(Panel(HELP_TEXT, title="Vercept Help", border_style="cyan"))
            continue

        if lower == "sessions":
            agent.list_sessions()
            continue

        if lower == "dry":
            config.dry_run = not config.dry_run
            state = "ON" if config.dry_run else "OFF"
            console.print(f"[yellow]Dry-run mode: {state}[/yellow]")
            continue

        # resume <task-id>
        if lower.startswith("resume "):
            parts = raw.split(None, 1)
            if len(parts) < 2 or not parts[1].strip():
                console.print("[yellow]Usage: resume <task-id>[/yellow]")
                continue
            task_id = parts[1].strip()
            # Load the instruction from session
            if agent.sessions:
                data = agent.sessions.load_task(task_id)
                if data:
                    instruction = data.get("instruction", "")
                    console.print(
                        f"[dim]Resuming: [bold]{instruction}[/bold][/dim]"
                    )
                    _running = True
                    try:
                        agent.run(instruction, resume_task_id=task_id)
                    except KeyboardInterrupt:
                        console.print("[yellow]Task interrupted.[/yellow]")
                    finally:
                        _running = False
                    continue
                else:
                    console.print(
                        f"[red]Session '{task_id}' not found.[/red]"
                    )
                    continue
            else:
                console.print("[yellow]Session storage is disabled.[/yellow]")
                continue

        # ── Run task ─────────────────────────────────────────────────────

        _running = True
        try:
            agent.run(raw)
        except KeyboardInterrupt:
            console.print("[yellow]Task interrupted.[/yellow]")
        finally:
            _running = False


if __name__ == "__main__":
    main()
