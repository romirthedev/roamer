import time

from rich.console import Console
from rich.panel import Panel

from config import VerceptConfig
from vercept.executor import Executor
from vercept.memory import TaskMemory
from vercept.perception import Perception
from vercept.planner import Planner
from vercept.safety import SafetyGuard

console = Console()


class Agent:
    def __init__(self, config: VerceptConfig):
        self.config = config
        self.perception = Perception(config)
        self.planner = Planner(config)
        self.executor = Executor(config)
        self.safety = SafetyGuard(config)

    def run(self, instruction: str) -> None:
        console.print(
            Panel(
                f"[bold]{instruction}[/bold]",
                title="Task",
                border_style="cyan",
            )
        )

        memory = TaskMemory(instruction=instruction)

        # Initial screen capture
        console.print("[dim]Capturing screen...[/dim]")
        screen = self.perception.capture()
        console.print(f"[dim]Screen: {screen.active_app} — {screen.description[:100]}[/dim]")

        while True:
            # Safety: action count limit
            if not self.safety.action_count_ok(memory.action_count):
                break

            # Plan next action
            console.print("[dim]Planning next action...[/dim]")
            action = self.planner.next_action(instruction, screen, memory)

            action_type = action.get("action_type", "unknown")
            reasoning = action.get("reasoning", "")
            is_final = action.get("is_final", False)

            # Check if task is complete
            if is_final or action_type == "done":
                console.print()
                console.print(
                    Panel(
                        f"[green]{reasoning}[/green]",
                        title="Task Complete",
                        border_style="green",
                    )
                )
                break

            # Display planned action
            console.print(
                f"  [bold cyan]Action {memory.action_count + 1}:[/bold cyan] "
                f"[bold]{action_type}[/bold] — {reasoning}"
            )
            params = action.get("params", {})
            if params:
                console.print(f"  [dim]Params: {params}[/dim]")

            # Safety: block sudo entirely
            if self.safety.block_sudo(action):
                memory.add_action(action, result="blocked_sudo")
                continue

            # Safety: check risky actions
            if not self.safety.check(action):
                console.print("  [yellow]Skipped by user.[/yellow]")
                memory.add_action(action, result="skipped_by_user")
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

            # Verify success
            verification = self.planner.verify_success(
                instruction, screen, new_screen, action
            )
            success = verification.get("success", True)
            explanation = verification.get("explanation", "")
            task_complete = verification.get("task_complete", False)

            # Update memory
            memory.add_action(
                action,
                result=explanation or result,
                screenshot_b64=new_screen.screenshot_base64,
            )

            if task_complete:
                console.print()
                console.print(
                    Panel(
                        f"[green]{explanation}[/green]",
                        title="Task Complete",
                        border_style="green",
                    )
                )
                break

            if success:
                memory.reset_retries()
                console.print(f"  [green]OK:[/green] {explanation}")
            else:
                memory.retry_count += 1
                console.print(f"  [yellow]Issue:[/yellow] {explanation}")
                if memory.retry_count >= memory.max_retries:
                    console.print(
                        "[yellow]Max retries reached for this step. Re-planning...[/yellow]"
                    )
                    memory.retry_count = 0

            console.print()
            screen = new_screen
