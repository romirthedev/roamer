import time

import pyautogui
from rich.console import Console

from config import VerceptConfig

console = Console()

# Disable pyautogui's failsafe pause for smoother execution,
# but keep the corner failsafe enabled (move mouse to corner to abort).
pyautogui.PAUSE = 0.1


class Executor:
    def __init__(self, config: VerceptConfig):
        self.config = config

    def execute(self, action: dict, screen_width: int, screen_height: int) -> str:
        """Execute an action. Returns a status string."""
        action_type = action.get("action_type", "")
        params = action.get("params", {})

        if self.config.dry_run:
            console.print(f"  [dim][DRY RUN] {action_type}: {params}[/dim]")
            return f"dry_run: {action_type}"

        try:
            if action_type == "click":
                return self._click(params, screen_width, screen_height)
            elif action_type == "type":
                return self._type_text(params)
            elif action_type == "scroll":
                return self._scroll(params)
            elif action_type == "hotkey":
                return self._hotkey(params)
            elif action_type == "drag":
                return self._drag(params, screen_width, screen_height)
            elif action_type == "wait":
                return self._wait(params)
            elif action_type == "done":
                return "task_complete"
            else:
                return f"unknown_action: {action_type}"
        except Exception as e:
            return f"execution_error: {e}"

    def _scale_coords(
        self, x: int, y: int, screen_width: int, screen_height: int
    ) -> tuple[int, int]:
        """Convert screenshot coordinates to actual screen coordinates.

        GPT-4o returns coords relative to the scaled screenshot.
        pyautogui uses logical screen points (not physical Retina pixels).
        """
        actual_w, actual_h = pyautogui.size()
        real_x = int(x * actual_w / screen_width)
        real_y = int(y * actual_h / screen_height)
        # Clamp to screen bounds
        real_x = max(0, min(real_x, actual_w - 1))
        real_y = max(0, min(real_y, actual_h - 1))
        return real_x, real_y

    def _click(
        self, params: dict, screen_width: int, screen_height: int
    ) -> str:
        x, y = self._scale_coords(
            params.get("x", 0), params.get("y", 0), screen_width, screen_height
        )
        button = params.get("button", "left")
        clicks = params.get("clicks", 1)
        pyautogui.click(x=x, y=y, button=button, clicks=clicks)
        return f"clicked ({x}, {y}) button={button} clicks={clicks}"

    def _type_text(self, params: dict) -> str:
        text = params.get("text", "")
        # Use write() for regular text, but handle special characters
        pyautogui.write(text, interval=0.03)
        return f"typed: {text[:50]}{'...' if len(text) > 50 else ''}"

    def _scroll(self, params: dict) -> str:
        direction = params.get("direction", "down")
        amount = params.get("amount", 3)
        scroll_val = amount if direction == "up" else -amount
        pyautogui.scroll(scroll_val)
        return f"scrolled {direction} by {amount}"

    def _hotkey(self, params: dict) -> str:
        keys = params.get("keys", [])
        if not keys:
            return "hotkey: no keys specified"
        # Map common names to pyautogui key names
        key_map = {
            "cmd": "command",
            "ctrl": "ctrl",
            "alt": "option",
            "option": "option",
            "shift": "shift",
            "enter": "return",
            "return": "return",
            "tab": "tab",
            "esc": "escape",
            "escape": "escape",
            "space": "space",
            "delete": "delete",
            "backspace": "backspace",
        }
        mapped_keys = [key_map.get(k.lower(), k.lower()) for k in keys]
        pyautogui.hotkey(*mapped_keys)
        return f"hotkey: {'+'.join(mapped_keys)}"

    def _drag(
        self, params: dict, screen_width: int, screen_height: int
    ) -> str:
        sx, sy = self._scale_coords(
            params.get("start_x", 0),
            params.get("start_y", 0),
            screen_width,
            screen_height,
        )
        ex, ey = self._scale_coords(
            params.get("end_x", 0),
            params.get("end_y", 0),
            screen_width,
            screen_height,
        )
        pyautogui.moveTo(sx, sy)
        time.sleep(0.1)
        pyautogui.drag(ex - sx, ey - sy, duration=0.5)
        return f"dragged ({sx},{sy}) -> ({ex},{ey})"

    def _wait(self, params: dict) -> str:
        seconds = min(params.get("seconds", 1.0), 10.0)  # Cap at 10s
        time.sleep(seconds)
        return f"waited {seconds}s"
