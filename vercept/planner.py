import json

from openai import OpenAI

from config import VerceptConfig
from vercept.memory import TaskMemory
from vercept.perception import ScreenState
from vercept.prompts import PLAN_PROMPT, VERIFY_PROMPT


class Planner:
    def __init__(self, config: VerceptConfig):
        self.config = config
        self.client = OpenAI(api_key=config.openai_api_key)

    def next_action(
        self, instruction: str, screen: ScreenState, memory: TaskMemory
    ) -> dict:
        """Determine the next action based on current screen and history."""
        history = memory.get_context_window()
        history_str = (
            json.dumps(history, indent=2) if history else "No actions taken yet."
        )

        prompt = PLAN_PROMPT.format(
            instruction=instruction,
            screen_description=screen.description,
            elements_json=json.dumps(screen.elements, indent=2),
            action_history=history_str,
            history_count=len(history),
            ocr_text=screen.ocr_text[:2000] if screen.ocr_text else "(none)",
            width=screen.screen_width,
            height=screen.screen_height,
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
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
                if raw.endswith("```"):
                    raw = raw[:-3]
                raw = raw.strip()
            return json.loads(raw)
        except (json.JSONDecodeError, Exception) as e:
            return {
                "action_type": "wait",
                "params": {"seconds": 1.0},
                "reasoning": f"Planning failed ({e}), waiting to retry.",
                "is_final": False,
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
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
                if raw.endswith("```"):
                    raw = raw[:-3]
                raw = raw.strip()
            return json.loads(raw)
        except (json.JSONDecodeError, Exception):
            return {
                "success": True,
                "explanation": "Verification unavailable, assuming success.",
                "task_complete": False,
            }
