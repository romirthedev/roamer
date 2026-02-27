import json
import os
import re
import time

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
    {"command", "q"},
]

# File extensions that warrant a warning
SENSITIVE_FILE_EXTENSIONS = {
    ".env", ".pem", ".key", ".p12", ".pfx", ".crt", ".cer",
    ".ssh", ".gpg", ".pgp", ".kdbx", ".1password",
}


class SafetyGuard:
    def __init__(self, config: VerceptConfig):
        self.config = config
        self._audit_file = os.path.expanduser(config.audit_log_path)
        if config.enable_audit_logging:
            os.makedirs(os.path.dirname(self._audit_file), exist_ok=True)

    # ── App restrictions ────────────────────────────────────────────────

    def check_app_allowed(self, app_name: str) -> bool:
        """Returns True if the active app is permitted."""
        if not app_name:
            return True

        # Whitelist check (if set, only these apps are allowed)
        if self.config.app_whitelist is not None:
            allowed = any(
                allowed_app.lower() in app_name.lower()
                for allowed_app in self.config.app_whitelist
            )
            if not allowed:
                console.print(
                    f"[red]App '{app_name}' is not in the whitelist. "
                    f"Allowed: {self.config.app_whitelist}[/red]"
                )
            return allowed

        # Blacklist check
        for blocked in self.config.app_blacklist:
            if blocked.lower() in app_name.lower():
                console.print(
                    f"[red]App '{app_name}' is blocked for safety. "
                    f"Blocked apps: {self.config.app_blacklist}[/red]"
                )
                return False

        return True

    # ── Action safety check ─────────────────────────────────────────────

    def check(self, action: dict) -> bool:
        """Returns True if the action is safe to proceed.
        Prompts the user if the action is risky.
        Returns False if the user rejects the action.
        """
        self._audit(action, "check")

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
            normalized = set()
            for k in keys:
                if k in ("cmd", "command"):
                    normalized.add("command")
                elif k in ("del", "delete"):
                    normalized.add("delete")
                elif k == "backspace":
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

        # File operations
        if action_type == "file_select":
            file_path = params.get("file_path", "")
            ext = os.path.splitext(file_path)[1].lower()
            if ext in SENSITIVE_FILE_EXTENSIONS:
                risk_reasons.append(f"Selecting a sensitive file type: {ext}")
            if self.config.confirm_file_operations:
                risk_reasons.append(f"File operation: {file_path}")

        # window_switch to blocked apps
        if action_type == "window_switch":
            app_name = params.get("app_name", "")
            if not self.check_app_allowed(app_name):
                console.print(f"[red]Blocked: switching to restricted app '{app_name}'.[/red]")
                return False

        if not risk_reasons:
            return True

        # Show risk and ask for confirmation
        console.print()
        console.print("[bold yellow]Safety Warning[/bold yellow]")
        console.print(f"  Action: {action_type} {params}")
        console.print(f"  Reason: {reasoning}")
        for reason in risk_reasons:
            console.print(f"  [yellow]Risk: {reason}[/yellow]")

        approved = Confirm.ask("  Proceed with this action?", default=False)
        self._audit(action, "approved" if approved else "denied_by_user")
        return approved

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
                self._audit(action, "blocked_sudo")
                return True
        return False

    # ── Audit logging ────────────────────────────────────────────────────

    def _audit(self, action: dict, event: str) -> None:
        if not self.config.enable_audit_logging:
            return
        try:
            action_type = action.get("action_type", "")
            params = action.get("params", {})

            # Redact text content so typed passwords and other sensitive
            # strings are not stored in plaintext in the audit log.
            if action_type == "type":
                params = {**params, "text": "[REDACTED]"}
            elif action_type == "form_fill":
                redacted_fields = [
                    {**f, "text": "[REDACTED]"} for f in params.get("fields", [])
                ]
                params = {**params, "fields": redacted_fields}

            entry = {
                "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "event": event,
                "action_type": action_type,
                "params": params,
            }
            with open(self._audit_file, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception:
            pass  # Never let audit logging break the agent
