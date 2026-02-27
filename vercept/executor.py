import subprocess
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

        dispatch = {
            "click": lambda: self._click(params, screen_width, screen_height),
            "double_click": lambda: self._double_click(params, screen_width, screen_height),
            "right_click": lambda: self._right_click(params, screen_width, screen_height),
            "triple_click": lambda: self._triple_click(params, screen_width, screen_height),
            "type": lambda: self._type_text(params),
            "key_press": lambda: self._key_press(params),
            "scroll": lambda: self._scroll(params),
            "hotkey": lambda: self._hotkey(params),
            "drag": lambda: self._drag(params, screen_width, screen_height),
            "select_all": lambda: self._select_all(params, screen_width, screen_height),
            "file_select": lambda: self._file_select(params),
            "window_switch": lambda: self._window_switch(params),
            "form_fill": lambda: self._form_fill(params, screen_width, screen_height),
            "wait": lambda: self._wait(params),
            "done": lambda: "task_complete",
        }

        handler = dispatch.get(action_type)
        if not handler:
            return f"unknown_action: {action_type}"

        try:
            return handler()
        except Exception as e:
            return f"execution_error: {e}"

    # ── Coordinate helpers ──────────────────────────────────────────────

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
        real_x = max(0, min(real_x, actual_w - 1))
        real_y = max(0, min(real_y, actual_h - 1))
        return real_x, real_y

    # ── Click actions ───────────────────────────────────────────────────

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

    def _double_click(
        self, params: dict, screen_width: int, screen_height: int
    ) -> str:
        x, y = self._scale_coords(
            params.get("x", 0), params.get("y", 0), screen_width, screen_height
        )
        pyautogui.doubleClick(x=x, y=y)
        return f"double_clicked ({x}, {y})"

    def _right_click(
        self, params: dict, screen_width: int, screen_height: int
    ) -> str:
        x, y = self._scale_coords(
            params.get("x", 0), params.get("y", 0), screen_width, screen_height
        )
        pyautogui.rightClick(x=x, y=y)
        return f"right_clicked ({x}, {y})"

    def _triple_click(
        self, params: dict, screen_width: int, screen_height: int
    ) -> str:
        x, y = self._scale_coords(
            params.get("x", 0), params.get("y", 0), screen_width, screen_height
        )
        pyautogui.click(x=x, y=y, clicks=3)
        return f"triple_clicked ({x}, {y})"

    # ── Keyboard actions ────────────────────────────────────────────────

    def _type_text(self, params: dict) -> str:
        text = params.get("text", "")
        pyautogui.write(text, interval=0.03)
        return f"typed: {text[:50]}{'...' if len(text) > 50 else ''}"

    def _key_press(self, params: dict) -> str:
        key = params.get("key", "")
        if not key:
            return "key_press: no key specified"
        key_map = {
            "enter": "return",
            "return": "return",
            "esc": "escape",
            "escape": "escape",
            "tab": "tab",
            "delete": "delete",
            "backspace": "backspace",
            "space": "space",
            "up": "up",
            "down": "down",
            "left": "left",
            "right": "right",
        }
        mapped = key_map.get(key.lower(), key.lower())
        pyautogui.press(mapped)
        return f"pressed: {mapped}"

    def _hotkey(self, params: dict) -> str:
        keys = params.get("keys", [])
        if not keys:
            return "hotkey: no keys specified"
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

    # ── Scroll ──────────────────────────────────────────────────────────

    def _scroll(self, params: dict) -> str:
        direction = params.get("direction", "down")
        amount = params.get("amount", 3)
        if direction in ("up", "down"):
            scroll_val = amount if direction == "up" else -amount
            pyautogui.scroll(scroll_val)
        elif direction == "left":
            pyautogui.hscroll(-amount)
        elif direction == "right":
            pyautogui.hscroll(amount)
        return f"scrolled {direction} by {amount}"

    # ── Drag ────────────────────────────────────────────────────────────

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

    # ── Select all ──────────────────────────────────────────────────────

    def _select_all(
        self, params: dict, screen_width: int, screen_height: int
    ) -> str:
        x, y = self._scale_coords(
            params.get("x", 0), params.get("y", 0), screen_width, screen_height
        )
        pyautogui.click(x=x, y=y)
        time.sleep(0.1)
        pyautogui.hotkey("command", "a")
        return f"select_all at ({x}, {y})"

    # ── File select (macOS) ─────────────────────────────────────────────

    def _file_select(self, params: dict) -> str:
        """Navigate a macOS Open/Save file dialog by typing the path directly."""
        file_path = params.get("file_path", "")
        if not file_path:
            return "file_select: no file_path specified"

        # On macOS, Cmd+Shift+G opens "Go to Folder" in file dialogs
        pyautogui.hotkey("command", "shift", "g")
        time.sleep(0.5)

        # Clear any existing text and type the path
        pyautogui.hotkey("command", "a")
        time.sleep(0.05)
        pyautogui.write(file_path, interval=0.02)
        time.sleep(0.3)

        # Press Enter to navigate to the path
        pyautogui.press("return")
        time.sleep(0.5)

        # Press Enter again to select/open the file
        pyautogui.press("return")
        time.sleep(0.3)

        return f"file_select: {file_path}"

    # ── Window switch (macOS) ───────────────────────────────────────────

    def _window_switch(self, params: dict) -> str:
        """Switch to a specific application using AppleScript on macOS."""
        app_name = params.get("app_name", "")
        if not app_name:
            return "window_switch: no app_name specified"

        try:
            subprocess.run(
                [
                    "osascript",
                    "-e",
                    f'tell application "{app_name}" to activate',
                ],
                timeout=5,
                capture_output=True,
            )
            time.sleep(0.5)
            return f"switched to: {app_name}"
        except subprocess.TimeoutExpired:
            return f"window_switch timeout: {app_name}"
        except Exception as e:
            return f"window_switch error: {e}"

    # ── Form fill ───────────────────────────────────────────────────────

    def _form_fill(
        self, params: dict, screen_width: int, screen_height: int
    ) -> str:
        """Fill multiple form fields in sequence."""
        fields = params.get("fields", [])
        if not fields:
            return "form_fill: no fields specified"

        filled = 0
        for field in fields:
            x, y = self._scale_coords(
                field.get("x", 0), field.get("y", 0), screen_width, screen_height
            )
            text = field.get("text", "")

            # Click field
            pyautogui.click(x=x, y=y)
            time.sleep(0.15)

            # Clear existing content
            pyautogui.hotkey("command", "a")
            time.sleep(0.05)
            pyautogui.press("delete")
            time.sleep(0.05)

            # Type new value
            pyautogui.write(text, interval=0.02)
            time.sleep(0.1)

            # Tab to next field
            pyautogui.press("tab")
            time.sleep(0.1)
            filled += 1

        return f"form_fill: filled {filled} field(s)"

    # ── Wait ────────────────────────────────────────────────────────────

    def _wait(self, params: dict) -> str:
        seconds = min(params.get("seconds", 1.0), 10.0)
        time.sleep(seconds)
        return f"waited {seconds}s"
