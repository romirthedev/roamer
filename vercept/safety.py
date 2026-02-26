import re

from rich.console import Console
from rich.prompt import Confirm

from config import VerceptConfig

console = Console()

# Patterns in typed text that are risky
RISKY_TEXT_PATTERNS = [
    re.compile(r"\bsudo\b", re.IGNORECASE),
    re.compile(r"\brm\s+-rf\b", re.IGNORECASE),
    re.compile(r"\bmkfs\b", re.IGNORECASE),
    re.compile(r"\bdd\s+if=", re.IGNORECASE),
    re.compile(r"\bformat\b", re.IGNORECASE),
    re.compile(r"password", re.IGNORECASE),
    re.compile(r"\bcurl\b.*\|\s*\bbash\b", re.IGNORECASE),
]

# Hotkey combos that are risky
RISKY_HOTKEYS = [
    {"command", "delete"},
    {"command", "backspace"},
    {"command", "q"},  # Quit app
]


class SafetyGuard:
    def __init__(self, config: VerceptConfig):
        self.config = config

    def check(self, action: dict) -> bool:
        """Returns True if the action is safe to proceed.
        Prompts the user if the action is risky.
        Returns False if the user rejects the action.
        """
        if not self.config.confirmation_required:
            return True

        action_type = action.get("action_type", "")
        params = action.get("params", {})
        reasoning = action.get("reasoning", "")

        risk_reasons = []

        if action_type == "type":
            text = params.get("text", "")
            for pattern in RISKY_TEXT_PATTERNS:
                if pattern.search(text):
                    risk_reasons.append(
                        f"Text contains risky pattern: {pattern.pattern}"
                    )

        if action_type == "hotkey":
            keys = {k.lower() for k in params.get("keys", [])}
            # Normalize key names
            normalized = set()
            for k in keys:
                if k in ("cmd", "command"):
                    normalized.add("command")
                elif k in ("del", "delete"):
                    normalized.add("delete")
                elif k in ("backspace",):
                    normalized.add("backspace")
                else:
                    normalized.add(k)
            for risky_combo in RISKY_HOTKEYS:
                if risky_combo.issubset(normalized):
                    risk_reasons.append(
                        f"Risky hotkey: {'+'.join(sorted(normalized))}"
                    )

        # Pressing Enter/Return could submit forms or run commands
        if action_type == "hotkey":
            keys_lower = [k.lower() for k in params.get("keys", [])]
            if any(k in ("enter", "return") for k in keys_lower):
                risk_reasons.append("Pressing Enter may submit a form or run a command")

        if not risk_reasons:
            return True

        # Show risk and ask for confirmation
        console.print()
        console.print("[bold yellow]Safety Warning[/bold yellow]")
        console.print(f"  Action: {action_type} {params}")
        console.print(f"  Reason: {reasoning}")
        for reason in risk_reasons:
            console.print(f"  [yellow]Risk: {reason}[/yellow]")

        return Confirm.ask("  Proceed with this action?", default=False)

    def action_count_ok(self, action_count: int) -> bool:
        if action_count >= self.config.max_actions_per_task:
            console.print(
                f"[red]Action limit reached ({self.config.max_actions_per_task}). "
                f"Stopping for safety.[/red]"
            )
            return False
        return True

    def block_sudo(self, action: dict) -> bool:
        """Returns True if the action should be blocked entirely (no user override)."""
        if action.get("action_type") == "type":
            text = action.get("params", {}).get("text", "")
            if re.search(r"\bsudo\b", text, re.IGNORECASE):
                console.print("[red]Blocked: agent attempted to type 'sudo'.[/red]")
                return True
        return False
