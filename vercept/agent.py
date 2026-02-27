import time

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from config import VerceptConfig
from vercept.executor import Executor
from vercept.memory import TaskMemory
from vercept.perception import Perception
from vercept.planner import Planner
from vercept.safety import SafetyGuard
from vercept.session_storage import SessionStorage
from vercept.state_verifier import quick_verify

console = Console()

# Number of consecutive failures before trying the fallback action
FALLBACK_THRESHOLD = 2
# Number of consecutive failures before aborting the task
ABORT_THRESHOLD = 5


class Agent:
    def __init__(self, config: VerceptConfig):
        self.config = config
        self.perception = Perception(config)
        self.planner = Planner(config)
        self.executor = Executor(config)
        self.safety = SafetyGuard(config)
        self.sessions = (
            SessionStorage(config.session_dir)
            if config.session_storage_enabled
            else None
        )

    # ── Public API ──────────────────────────────────────────────────────

    def run(self, instruction: str, resume_task_id: str | None = None) -> None:
        """Run a task from start (or resume a previous session)."""
        memory = self._init_memory(instruction, resume_task_id)

        console.print(
            Panel(
                f"[bold]{instruction}[/bold]\n"
                f"[dim]Task ID: {memory.task_id}[/dim]",
                title="Task",
                border_style="cyan",
            )
        )

        if resume_task_id and memory.action_count > 0:
            console.print(
                f"[dim]Resuming session {resume_task_id} — "
                f"{memory.action_count} previous action(s).[/dim]"
            )

        # Initial screen capture
        console.print("[dim]Capturing screen...[/dim]")
        screen = self.perception.capture()

        if screen.perception_failed:
            console.print(
                "[red]Initial screen analysis failed. Cannot start task.[/red]"
            )
            return

        self._log_screen(screen)

        # Safety: check the currently active app
        if not self.safety.check_app_allowed(screen.active_app):
            console.print(
                f"[red]Active app '{screen.active_app}' is restricted. "
                "Please switch to an allowed app.[/red]"
            )
            return

        try:
            self._run_loop(instruction, screen, memory)
        finally:
            self._save_session(memory)

    def list_sessions(self) -> None:
        """Print recent sessions to the console."""
        if not self.sessions:
            console.print("[dim]Session storage is disabled.[/dim]")
            return

        tasks = self.sessions.list_tasks()
        if not tasks:
            console.print("[dim]No saved sessions.[/dim]")
            return

        table = Table(title="Recent Sessions", border_style="cyan")
        table.add_column("ID", style="bold cyan")
        table.add_column("Instruction")
        table.add_column("Actions", justify="right")
        table.add_column("Status")
        table.add_column("Saved")

        for t in tasks:
            status = (
                "[green]Done[/green]"
                if t.get("completed")
                else "[yellow]Partial[/yellow]"
            )
            saved = time.strftime(
                "%m/%d %H:%M", time.localtime(t.get("saved_at", 0))
            )
            instruction = t.get("instruction", "")[:50]
            if len(t.get("instruction", "")) > 50:
                instruction += "…"
            table.add_row(
                t["task_id"],
                instruction,
                str(t.get("action_count", 0)),
                status,
                saved,
            )

        console.print(table)

    # ── Core loop ────────────────────────────────────────────────────────

    def _run_loop(self, instruction: str, screen, memory: TaskMemory) -> None:
        # Track how long we've been stuck on a loading screen so we don't
        # loop forever if the VLM persistently misidentifies the state.
        loading_wait_start: float | None = None

        while True:
            # Safety: action count limit
            if not self.safety.action_count_ok(memory.action_count):
                break

            # Safety: task duration limit
            if memory.elapsed_seconds > self.config.max_task_duration:
                console.print(
                    f"[red]Task duration limit reached "
                    f"({self.config.max_task_duration}s). Stopping.[/red]"
                )
                break

            # Safety: re-check the active app on every iteration so that
            # mid-task app switches (via window_switch or link clicks) are
            # caught, not just the initial check.
            if screen.active_app and not self.safety.check_app_allowed(
                screen.active_app
            ):
                console.print(
                    f"[red]Active app changed to restricted app "
                    f"'{screen.active_app}'. Stopping.[/red]"
                )
                break

            # If screen is loading, wait and re-capture — but enforce a timeout
            # so a persistently misidentified loading state doesn't spin forever.
            if screen.loading:
                if loading_wait_start is None:
                    loading_wait_start = time.time()
                elif (
                    time.time() - loading_wait_start
                    > self.config.loading_wait_timeout
                ):
                    console.print(
                        f"[red]Loading timeout "
                        f"({self.config.loading_wait_timeout}s). Stopping.[/red]"
                    )
                    break
                console.print("[dim]Screen is loading — waiting...[/dim]")
                time.sleep(2.0)
                screen = self.perception.capture()
                continue
            else:
                loading_wait_start = None  # reset once loading clears

            # Abort if too many consecutive failures
            if memory.consecutive_failures >= ABORT_THRESHOLD:
                console.print(
                    Panel(
                        f"[red]Aborting: {memory.consecutive_failures} consecutive "
                        f"failures. Last: "
                        f"{memory.actions_taken[-1].get('result', '') if memory.actions_taken else ''}[/red]",
                        title="Task Aborted",
                        border_style="red",
                    )
                )
                break

            # Plan next action
            console.print("[dim]Planning...[/dim]")
            action = self.planner.next_action(instruction, screen, memory)

            # If we've been failing and a fallback was provided, swap it in.
            # Use a non-destructive merge so the original reasoning is preserved
            # in the log for traceability.
            if (
                memory.consecutive_failures >= FALLBACK_THRESHOLD
                and action.get("fallback_action")
                and action.get("confidence", "high") in ("low", "medium")
            ):
                fallback = action["fallback_action"]
                original_reasoning = action.get("reasoning", "")
                console.print(
                    f"  [yellow]Using fallback due to "
                    f"{memory.consecutive_failures} failures.[/yellow]"
                )
                # Build a new dict so the original action is not mutated
                action = {**action, **fallback}
                fallback_reasoning = fallback.get("reasoning", "")
                if fallback_reasoning and fallback_reasoning != original_reasoning:
                    action["reasoning"] = (
                        f"[Fallback] {fallback_reasoning}"
                        + (f" (was: {original_reasoning})" if original_reasoning else "")
                    )

            action_type = action.get("action_type", "unknown")
            reasoning = action.get("reasoning", "")
            is_final = action.get("is_final", False)
            confidence = action.get("confidence", "high")

            # Check if task is complete
            if is_final or action_type == "done":
                memory.completed = True
                summary = self.planner.summarize_actions(memory.actions_taken)
                console.print()
                console.print(
                    Panel(
                        f"[green]{reasoning}[/green]\n\n[dim]{summary}[/dim]",
                        title="Task Complete",
                        border_style="green",
                    )
                )
                break

            # Display planned action
            conf_color = {"high": "green", "medium": "yellow", "low": "red"}.get(
                confidence, "white"
            )
            console.print(
                f"  [bold cyan]Action {memory.action_count + 1}:[/bold cyan] "
                f"[bold]{action_type}[/bold] — {reasoning} "
                f"[{conf_color}]({confidence})[/{conf_color}]"
            )
            params = action.get("params", {})
            if params:
                console.print(f"  [dim]Params: {params}[/dim]")

            # Safety: block sudo entirely (no user override).
            # Mark as neutral so a blocked sudo doesn't count toward the
            # consecutive-failure abort counter.
            if self.safety.block_sudo(action):
                memory.add_action(
                    action, result="blocked_sudo", success=False, neutral=True
                )
                continue

            # Safety: check risky actions (user confirmation prompt).
            # A user choosing to skip an action is not a task failure — mark
            # neutral so skips don't accumulate toward the abort threshold.
            if not self.safety.check(action):
                console.print("  [yellow]Skipped by user.[/yellow]")
                memory.add_action(
                    action, result="skipped_by_user", success=False, neutral=True
                )
                continue

            # Execute
            result = self.executor.execute(
                action, screen.screen_width, screen.screen_height
            )
            console.print(f"  [dim]Result: {result}[/dim]")

            # Wait for UI to settle
            time.sleep(self.config.action_delay)

            # Capture new state
            console.print("[dim]Verifying...[/dim]")
            new_screen = self.perception.capture()

            # If perception failed, count it as a failure and keep the last
            # known-good screen state for context on the next planning pass.
            # This prevents the agent from looping indefinitely on wait
            # actions whose heuristic verification always returns success.
            if new_screen.perception_failed:
                console.print(
                    "[yellow]Screen analysis failed — counting as step failure.[/yellow]"
                )
                memory.add_action(action, result="perception_failed", success=False)
                # Do not update screen — preserve last known-good state
                console.print()
                continue

            # Try fast-path heuristic verification first
            verification = quick_verify(
                screen,
                new_screen,
                action,
                self.config.change_detection_threshold,
            )

            # Fall back to LLM verification when heuristics can't decide
            if verification is None:
                verification = self.planner.verify_success(
                    instruction, screen, new_screen, action
                )

            success = verification.get("success", True)
            explanation = verification.get("explanation", "")
            task_complete = verification.get("task_complete", False)
            screen_changed = verification.get("screen_changed", True)

            # Update memory (no screenshot stored — it was never read back and
            # accumulated ~500 KB per action in RAM for a 50-action task)
            memory.add_action(
                action,
                result=explanation or result,
                success=success,
            )

            if task_complete:
                memory.completed = True
                summary = self.planner.summarize_actions(memory.actions_taken)
                console.print()
                console.print(
                    Panel(
                        f"[green]{explanation}[/green]\n\n[dim]{summary}[/dim]",
                        title="Task Complete",
                        border_style="green",
                    )
                )
                break

            if success:
                console.print(f"  [green]OK:[/green] {explanation}")
            else:
                console.print(f"  [yellow]Issue:[/yellow] {explanation}")
                if not screen_changed:
                    console.print(
                        "  [dim]Screen unchanged — action may not have had effect.[/dim]"
                    )

            console.print()
            screen = new_screen

    # ── Helpers ──────────────────────────────────────────────────────────

    def _init_memory(self, instruction: str, resume_task_id: str | None) -> TaskMemory:
        if resume_task_id and self.sessions:
            data = self.sessions.load_task(resume_task_id)
            if data:
                return TaskMemory.from_dict(data)
            console.print(
                f"[yellow]Session '{resume_task_id}' not found. Starting fresh.[/yellow]"
            )
        return TaskMemory(instruction=instruction)

    def _save_session(self, memory: TaskMemory) -> None:
        if self.sessions and memory.action_count > 0:
            task_id = self.sessions.save_task(memory.to_dict())
            console.print(f"[dim]Session saved: {task_id}[/dim]")

    def _log_screen(self, screen) -> None:
        app = screen.active_app or "Unknown"
        desc = screen.description[:120] if screen.description else "No description"
        console.print(f"[dim]Screen: [bold]{app}[/bold] — {desc}[/dim]")
        if screen.errors:
            console.print(f"[yellow]Screen errors: {screen.errors}[/yellow]")
        if screen.loading:
            console.print("[dim]Screen is loading...[/dim]")
