import json

from openai import OpenAI

from config import VerceptConfig
from vercept.memory import TaskMemory
from vercept.perception import ScreenState
from vercept.prompts import (
    PLAN_PROMPT,
    PLAN_PROMPT_FAILURE_CONTEXT,
    PLAN_PROMPT_RESUMED_NOTE,
    VERIFY_PROMPT,
    SUMMARIZE_PROMPT,
)


class Planner:
    def __init__(self, config: VerceptConfig):
        self.config = config
        # Apply action_timeout so a hung API call doesn't stall the agent
        # indefinitely.  The config default is 30s; the SDK default is 600s.
        self.client = OpenAI(
            api_key=config.openai_api_key,
            timeout=config.action_timeout,
        )

    def next_action(
        self, instruction: str, screen: ScreenState, memory: TaskMemory
    ) -> dict:
        """Determine the next action based on current screen and history."""
        history = memory.get_context_window()
        history_str = (
            json.dumps(history, indent=2) if history else "No actions taken yet."
        )

        # Build failure context block if we've been failing
        failure_context = ""
        if memory.consecutive_failures >= 2:
            failed = memory.get_failure_context()
            failure_context = PLAN_PROMPT_FAILURE_CONTEXT.format(
                failure_count=memory.consecutive_failures,
                failed_actions=json.dumps(failed, indent=2),
            )

        # Warn the model when picking up an interrupted session so it doesn't
        # blindly re-execute steps that may already be done on the live screen.
        resumed_note = PLAN_PROMPT_RESUMED_NOTE if memory.resumed else ""

        prompt = PLAN_PROMPT.format(
            instruction=instruction,
            screen_description=screen.description,
            elements_json=json.dumps(screen.elements, indent=2),
            action_history=history_str,
            history_count=len(history),
            ocr_text=screen.ocr_text[:2000] if screen.ocr_text else "(none)",
            width=screen.screen_width,
            height=screen.screen_height,
            failure_context=failure_context,
            resumed_note=resumed_note,
        )

        try:
            response = self.client.chat.completions.create(
                model=self.config.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{screen.screenshot_base64}",
                                    "detail": "high",
                                },
                            },
                        ],
                    }
                ],
                max_tokens=1000,
                temperature=0,
            )
            raw = response.choices[0].message.content.strip()
            raw = self._strip_fences(raw)
            return json.loads(raw)
        except (json.JSONDecodeError, Exception) as e:
            return {
                "action_type": "wait",
                "params": {"seconds": 1.0},
                "reasoning": f"Planning failed ({e}), waiting to retry.",
                "is_final": False,
                "confidence": "low",
                "fallback_action": None,
            }

    def verify_success(
        self,
        instruction: str,
        before: ScreenState,
        after: ScreenState,
        action: dict,
    ) -> dict:
        """Check if the last action succeeded by comparing before/after screenshots."""
        action_desc = f"{action.get('action_type', '')} {action.get('params', {})}"

        prompt = VERIFY_PROMPT.format(
            action_type=action.get("action_type", ""),
            action_description=action_desc,
            reasoning=action.get("reasoning", ""),
            instruction=instruction,
        )

        try:
            response = self.client.chat.completions.create(
                model=self.config.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{before.screenshot_base64}",
                                    "detail": "low",
                                },
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{after.screenshot_base64}",
                                    "detail": "low",
                                },
                            },
                        ],
                    }
                ],
                max_tokens=500,
                temperature=0,
            )
            raw = response.choices[0].message.content.strip()
            raw = self._strip_fences(raw)
            return json.loads(raw)
        except (json.JSONDecodeError, Exception):
            return {
                "success": True,
                "explanation": "Verification unavailable, assuming success.",
                "task_complete": False,
                "confidence": "low",
                "screen_changed": True,
            }

    def summarize_actions(self, actions: list[dict]) -> str:
        """Use the LLM to produce a short summary of completed actions."""
        if not actions:
            return "No actions taken."

        actions_text = "\n".join(
            f"{i+1}. {a.get('action_type','')}: {a.get('reasoning','')[:80]}"
            for i, a in enumerate(actions)
        )
        prompt = SUMMARIZE_PROMPT.format(
            count=len(actions), actions_text=actions_text
        )

        try:
            response = self.client.chat.completions.create(
                model=self.config.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=150,
                temperature=0,
            )
            return response.choices[0].message.content.strip()
        except Exception:
            return f"Completed {len(actions)} action(s)."

    @staticmethod
    def _strip_fences(raw: str) -> str:
        """Strip markdown code fences from LLM JSON output."""
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
            if raw.endswith("```"):
                raw = raw[:-3]
        return raw.strip()
