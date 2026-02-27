import time
import uuid
from dataclasses import dataclass, field


@dataclass
class TaskMemory:
    instruction: str
    actions_taken: list[dict] = field(default_factory=list)
    retry_count: int = 0
    max_retries: int = 3
    task_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    started_at: float = field(default_factory=time.time)
    completed: bool = False

    # Failure tracking for replanning
    consecutive_failures: int = 0
    failed_actions: list[dict] = field(default_factory=list)

    def add_action(
        self, action: dict, result: str, screenshot_b64: str = "", success: bool = True
    ) -> None:
        entry = {
            "action_type": action.get("action_type", ""),
            "params": action.get("params", {}),
            "reasoning": action.get("reasoning", ""),
            "result": result,
            "screenshot_b64": screenshot_b64,
            "success": success,
            "timestamp": time.time(),
        }
        self.actions_taken.append(entry)

        if not success:
            self.consecutive_failures += 1
            self.failed_actions.append(entry)
        else:
            self.consecutive_failures = 0
            self.failed_actions.clear()

    def get_context_window(self, last_n: int = 5) -> list[dict]:
        """Return the last N actions for LLM context (without screenshots to save tokens)."""
        recent = self.actions_taken[-last_n:]
        return [
            {
                "action_type": a["action_type"],
                "params": a["params"],
                "reasoning": a["reasoning"],
                "result": a["result"],
                "success": a.get("success", True),
            }
            for a in recent
        ]

    def get_failure_context(self) -> list[dict]:
        """Return recent failed actions for replanning context."""
        return [
            {
                "action_type": a["action_type"],
                "params": a["params"],
                "result": a["result"],
            }
            for a in self.failed_actions[-3:]
        ]

    def summarize_actions(self) -> str:
        """Generate a brief summary of all actions taken so far."""
        if not self.actions_taken:
            return "No actions taken yet."

        lines = []
        for i, a in enumerate(self.actions_taken, 1):
            status = "OK" if a.get("success", True) else "FAILED"
            lines.append(
                f"  {i}. [{status}] {a['action_type']}: {a.get('reasoning', '')[:60]}"
            )
        return "\n".join(lines)

    def reset_retries(self) -> None:
        self.retry_count = 0

    @property
    def action_count(self) -> int:
        return len(self.actions_taken)

    @property
    def elapsed_seconds(self) -> float:
        return time.time() - self.started_at

    def to_dict(self) -> dict:
        """Serialize for session persistence (strips screenshots to save space)."""
        actions = []
        for a in self.actions_taken:
            actions.append({
                "action_type": a["action_type"],
                "params": a["params"],
                "reasoning": a["reasoning"],
                "result": a["result"],
                "success": a.get("success", True),
                "timestamp": a.get("timestamp", 0),
            })
        return {
            "task_id": self.task_id,
            "instruction": self.instruction,
            "actions": actions,
            "action_count": self.action_count,
            "started_at": self.started_at,
            "completed": self.completed,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TaskMemory":
        """Restore from serialized dict."""
        mem = cls(
            instruction=data.get("instruction", ""),
            task_id=data.get("task_id", str(uuid.uuid4())[:8]),
            started_at=data.get("started_at", time.time()),
            completed=data.get("completed", False),
        )
        for a in data.get("actions", []):
            mem.actions_taken.append({
                "action_type": a.get("action_type", ""),
                "params": a.get("params", {}),
                "reasoning": a.get("reasoning", ""),
                "result": a.get("result", ""),
                "screenshot_b64": "",
                "success": a.get("success", True),
                "timestamp": a.get("timestamp", 0),
            })
        return mem
