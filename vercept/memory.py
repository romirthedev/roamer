from dataclasses import dataclass, field


@dataclass
class TaskMemory:
    instruction: str
    actions_taken: list[dict] = field(default_factory=list)
    retry_count: int = 0
    max_retries: int = 3

    def add_action(
        self, action: dict, result: str, screenshot_b64: str = ""
    ) -> None:
        self.actions_taken.append(
            {
                "action_type": action.get("action_type", ""),
                "params": action.get("params", {}),
                "reasoning": action.get("reasoning", ""),
                "result": result,
                "screenshot_b64": screenshot_b64,
            }
        )

    def get_context_window(self, last_n: int = 5) -> list[dict]:
        """Return the last N actions for LLM context (without screenshots to save tokens)."""
        recent = self.actions_taken[-last_n:]
        return [
            {
                "action_type": a["action_type"],
                "params": a["params"],
                "reasoning": a["reasoning"],
                "result": a["result"],
            }
            for a in recent
        ]

    def reset_retries(self) -> None:
        self.retry_count = 0

    @property
    def action_count(self) -> int:
        return len(self.actions_taken)
