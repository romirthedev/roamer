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
            # scroll now receives screen dimensions so it can position the mouse
            "scroll": lambda: self._scroll(params, screen_width, screen_height),
            "hotkey": lambda: self._hotkey(params),
            "drag": lambda: self._drag(params, screen_width, screen_height),
            "select_all": lambda: self._select_all(params, screen_width, screen_height),
            "file_select": lambda: self._file_select(params),
            "window_switch": lambda: self._window_switch(params),
            "navigate": lambda: self._navigate(params),
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

    # ── Clipboard helper ────────────────────────────────────────────────

    @staticmethod
    def _paste_via_clipboard(text: str) -> bool:
        """Copy text to macOS clipboard and paste with Cmd+V.

        Returns True on success, False if pbcopy is unavailable (non-macOS).
        Handles all Unicode characters that pyautogui.write() cannot.
        """
        try:
            subprocess.run(
                ["pbcopy"],
                input=text.encode("utf-8"),
                timeout=5,
                check=True,
            )
            time.sleep(0.05)
            pyautogui.hotkey("command", "v")
            return True
        except FileNotFoundError:
            # pbcopy not present — caller should fall back to pyautogui.write
            return False

    # ── Click actions ───────────────────────────────────────────────────

    def _click(
        self, params: dict, screen_width: int, screen_height: int
    ) -> str:
        if "x" not in params or "y" not in params:
            return "click: missing x or y coordinate — cannot click without a target"
        x, y = self._scale_coords(
            int(params["x"]), int(params["y"]), screen_width, screen_height
        )
        button = params.get("button", "left")
        clicks = params.get("clicks", 1)
        pyautogui.click(x=x, y=y, button=button, clicks=clicks)
        return f"clicked ({x}, {y}) button={button} clicks={clicks}"

    def _double_click(
        self, params: dict, screen_width: int, screen_height: int
    ) -> str:
        if "x" not in params or "y" not in params:
            return "double_click: missing x or y coordinate"
        x, y = self._scale_coords(
            int(params["x"]), int(params["y"]), screen_width, screen_height
        )
        pyautogui.doubleClick(x=x, y=y)
        return f"double_clicked ({x}, {y})"

    def _right_click(
        self, params: dict, screen_width: int, screen_height: int
    ) -> str:
        if "x" not in params or "y" not in params:
            return "right_click: missing x or y coordinate"
        x, y = self._scale_coords(
            int(params["x"]), int(params["y"]), screen_width, screen_height
        )
        pyautogui.rightClick(x=x, y=y)
        return f"right_clicked ({x}, {y})"

    def _triple_click(
        self, params: dict, screen_width: int, screen_height: int
    ) -> str:
        if "x" not in params or "y" not in params:
            return "triple_click: missing x or y coordinate"
        x, y = self._scale_coords(
            int(params["x"]), int(params["y"]), screen_width, screen_height
        )
        pyautogui.click(x=x, y=y, clicks=3)
        return f"triple_clicked ({x}, {y})"

    # ── Keyboard actions ────────────────────────────────────────────────

    def _type_text(self, params: dict) -> str:
        """Type text using clipboard paste for full Unicode support.

        pyautogui.write() only handles basic ASCII keycodes and breaks for
        accented characters, emoji, CJK, and many special symbols.  Using
        pbcopy + Cmd+V bypasses that limitation entirely.
        """
        text = params.get("text", "")
        if not text:
            return "typed: (empty)"

        if self._paste_via_clipboard(text):
            return f"typed (clipboard): {text[:50]}{'...' if len(text) > 50 else ''}"

        # Fallback: pyautogui.write for environments without pbcopy
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
            # Function keys — explicitly mapped so intent is clear
            **{f"f{i}": f"f{i}" for i in range(1, 13)},
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

    def _scroll(self, params: dict, screen_width: int, screen_height: int) -> str:
        """Scroll in the given direction.

        Optional params 'x' and 'y' move the mouse to the scroll target first,
        so the correct scrollable area receives the event (e.g. a sidebar vs
        the main content pane).

        Horizontal scroll uses pyautogui.hscroll when available, falling back
        to Shift+vertical-scroll which most macOS apps treat as horizontal.
        """
        direction = params.get("direction", "down")
        amount = params.get("amount", 3)

        # Position the cursor over the intended scroll target
        x = params.get("x")
        y = params.get("y")
        if x is not None and y is not None:
            rx, ry = self._scale_coords(int(x), int(y), screen_width, screen_height)
            pyautogui.moveTo(rx, ry)
            time.sleep(0.05)

        if direction in ("up", "down"):
            scroll_val = amount if direction == "up" else -amount
            pyautogui.scroll(scroll_val)
        elif direction in ("left", "right"):
            hscroll_fn = getattr(pyautogui, "hscroll", None)
            if callable(hscroll_fn):
                val = -amount if direction == "left" else amount
                hscroll_fn(val)
            else:
                # Shift+scroll is treated as horizontal scroll in most macOS apps
                pyautogui.keyDown("shift")
                val = amount if direction == "left" else -amount
                pyautogui.scroll(val)
                pyautogui.keyUp("shift")

        return f"scrolled {direction} by {amount}"

    # ── Drag ────────────────────────────────────────────────────────────

    def _drag(
        self, params: dict, screen_width: int, screen_height: int
    ) -> str:
        for key in ("start_x", "start_y", "end_x", "end_y"):
            if key not in params:
                return f"drag: missing required param '{key}'"
        sx, sy = self._scale_coords(
            int(params["start_x"]),
            int(params["start_y"]),
            screen_width,
            screen_height,
        )
        ex, ey = self._scale_coords(
            int(params["end_x"]),
            int(params["end_y"]),
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
        """Select all text in a field.

        If explicit x/y coordinates are provided, click the field first.
        Without coordinates we skip the click to avoid accidentally activating
        whatever lives at (0, 0) — the macOS Apple menu — and just issue Cmd+A
        to the currently focused element.
        """
        if "x" in params and "y" in params:
            x, y = self._scale_coords(
                int(params["x"]), int(params["y"]), screen_width, screen_height
            )
            pyautogui.click(x=x, y=y)
            time.sleep(0.1)
            loc = f"({x}, {y})"
        else:
            loc = "(current focus)"

        pyautogui.hotkey("command", "a")
        return f"select_all at {loc}"

    # ── File select (macOS) ─────────────────────────────────────────────

    def _file_select(self, params: dict) -> str:
        """Navigate a macOS Open/Save file dialog to the given path.

        Uses clipboard paste (pbcopy) instead of pyautogui.write() so paths
        with spaces, Unicode, or special characters are entered correctly.

        Note: Cmd+Shift+G only works inside native macOS file dialogs and
        Finder.  Electron or custom file pickers require a different approach.
        """
        file_path = params.get("file_path", "")
        if not file_path:
            return "file_select: no file_path specified"

        # Place the path on the clipboard before opening the dialog
        try:
            subprocess.run(
                ["pbcopy"],
                input=file_path.encode("utf-8"),
                timeout=5,
                check=True,
            )
        except FileNotFoundError:
            return "file_select: pbcopy unavailable — cannot set clipboard path"
        except Exception as e:
            return f"file_select: clipboard setup failed: {e}"

        # Open "Go to Folder" sheet inside the file dialog
        pyautogui.hotkey("command", "shift", "g")
        time.sleep(max(0.5, self.config.file_dialog_timeout * 0.15))

        # Select any pre-filled text and paste the path
        pyautogui.hotkey("command", "a")
        time.sleep(0.05)
        pyautogui.hotkey("command", "v")
        time.sleep(0.3)

        # Navigate to the directory
        pyautogui.press("return")
        time.sleep(0.5)

        # Confirm/select the file
        pyautogui.press("return")
        time.sleep(0.3)

        return f"file_select: {file_path}"

    # ── Window switch (macOS) ───────────────────────────────────────────

    def _window_switch(self, params: dict) -> str:
        """Bring a specific application to the front using AppleScript."""
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

    # ── Browser navigation ──────────────────────────────────────────────

    # URL schemes that should be passed directly to `open` without modification.
    # Anything not in this list is treated as a bare search term and wrapped
    # in a Google search URL.
    _KNOWN_SCHEMES = ("http://", "https://", "file://", "mailto:")

    def _navigate(self, params: dict) -> str:
        """Open a URL, mailto link, or search term via the macOS `open` command.

        Works regardless of which app currently has focus — no Cmd+L required.
        `open` hands the target off to the OS; the appropriate app (browser or
        mail client) brings itself to front and handles the request.

        Recognized schemes: http, https, file, mailto.
        Anything else is treated as a search term and opened via Google.
        """
        import urllib.parse

        url = params.get("url", "")
        if not url:
            return "navigate: no url specified"

        # Routing logic (evaluated in order):
        # 1. Recognized scheme (http/https/file/mailto) → use as-is
        # 2. Looks like a hostname/path (no spaces, contains "." or is localhost)
        #    → prepend https://  e.g. "docs.python.org" → "https://docs.python.org"
        # 3. Everything else is a search term → wrap in Google search URL
        if any(url.startswith(p) for p in self._KNOWN_SCHEMES):
            pass  # already a valid URL
        elif " " not in url and ("." in url or url.startswith("localhost")):
            url = "https://" + url
        else:
            url = "https://www.google.com/search?q=" + urllib.parse.quote_plus(url)

        try:
            subprocess.run(["open", url], timeout=10, check=True)
            # Longer delay so the browser has time to activate and render
            # before the next perception call; insufficient delay causes the
            # planner to see VS Code still and re-issue navigate.
            time.sleep(1.5)
            return f"navigate: {url}"
        except subprocess.TimeoutExpired:
            return "navigate: open command timed out"
        except Exception as e:
            return f"navigate error: {e}"

    # ── Form fill ───────────────────────────────────────────────────────

    def _form_fill(
        self, params: dict, screen_width: int, screen_height: int
    ) -> str:
        """Fill multiple form fields in sequence.

        Uses triple-click to focus each field and select any pre-existing
        content (more reliable than click + Cmd+A for most input types).
        Text is entered via clipboard paste for full Unicode support.
        """
        fields = params.get("fields", [])
        if not fields:
            return "form_fill: no fields specified"

        filled = 0
        for field in fields:
            x, y = self._scale_coords(
                field.get("x", 0), field.get("y", 0), screen_width, screen_height
            )
            text = field.get("text", "")

            # Triple-click focuses the field and selects any existing text
            pyautogui.click(x=x, y=y, clicks=3)
            time.sleep(0.2)  # allow focus to settle

            # Type via clipboard so Unicode / special chars work
            if not self._paste_via_clipboard(text):
                # pbcopy unavailable — fall back to direct typing
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
