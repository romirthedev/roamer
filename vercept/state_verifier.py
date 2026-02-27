"""Fast-path heuristic verification to reduce LLM calls.

Returns a verification result when confident, or None to fall back to the LLM.
"""

from vercept.perception import ScreenState
from vercept.screen_diff import compare_screens


def quick_verify(
    before: ScreenState,
    after: ScreenState,
    action: dict,
    threshold: float = 0.02,
) -> dict | None:
    """Try to verify an action heuristically without calling the LLM.

    Returns:
        dict with {success, explanation, task_complete, confidence, screen_changed}
        or None if we can't verify heuristically (fall back to LLM).
    """
    action_type = action.get("action_type", "")
    diff = compare_screens(before.screenshot_base64, after.screenshot_base64, threshold)

    screen_changed = diff["changed"]
    diff_ratio = diff["diff_ratio"]

    # Scroll: almost always succeeds if screen changed
    if action_type == "scroll":
        if screen_changed:
            return {
                "success": True,
                "explanation": f"Screen changed after scroll (diff {diff_ratio:.1%}).",
                "task_complete": False,
                "confidence": "high",
                "screen_changed": True,
            }
        return {
            "success": False,
            "explanation": "Screen did not change after scroll — may be at page boundary.",
            "task_complete": False,
            "confidence": "medium",
            "screen_changed": False,
        }

    # Wait: always "succeeds" (it's just a delay)
    if action_type == "wait":
        return {
            "success": True,
            "explanation": "Wait completed.",
            "task_complete": False,
            "confidence": "high",
            "screen_changed": screen_changed,
        }

    # Type: if screen changed, text was likely typed
    if action_type == "type":
        if screen_changed:
            return {
                "success": True,
                "explanation": f"Screen changed after typing (diff {diff_ratio:.1%}).",
                "task_complete": False,
                "confidence": "medium",
                "screen_changed": True,
            }
        # Screen didn't change — the text field might not have been focused
        return None  # Let LLM decide

    # Key press: if screen changed, key likely had effect
    if action_type == "key_press":
        key = action.get("params", {}).get("key", "")
        if screen_changed:
            return {
                "success": True,
                "explanation": f"Screen changed after pressing '{key}'.",
                "task_complete": False,
                "confidence": "medium",
                "screen_changed": True,
            }
        # Some key presses have no visible effect (e.g., copy)
        return None

    # Hotkey: copy/cut have no visible effect, others do
    if action_type == "hotkey":
        keys = action.get("params", {}).get("keys", [])
        keys_lower = [k.lower() for k in keys]
        invisible_combos = [
            ["cmd", "c"],   # copy
            ["cmd", "x"],   # cut (clipboard, not always visible)
            ["command", "c"],
            ["command", "x"],
        ]
        is_invisible = any(
            sorted(keys_lower) == sorted(combo) for combo in invisible_combos
        )
        if is_invisible:
            return {
                "success": True,
                "explanation": f"Hotkey {'+'.join(keys)} executed (no visible change expected).",
                "task_complete": False,
                "confidence": "medium",
                "screen_changed": screen_changed,
            }
        if screen_changed:
            return {
                "success": True,
                "explanation": f"Screen changed after hotkey {'+'.join(keys)}.",
                "task_complete": False,
                "confidence": "medium",
                "screen_changed": True,
            }
        return None

    # Click / double_click / right_click / triple_click: need LLM for context
    if action_type in ("click", "double_click", "right_click", "triple_click"):
        if screen_changed and diff_ratio > 0.05:
            # Big visual change — likely something opened/happened
            return {
                "success": True,
                "explanation": f"Significant screen change after {action_type} "
                               f"(diff {diff_ratio:.1%}).",
                "task_complete": False,
                "confidence": "medium",
                "screen_changed": True,
            }
        # Small or no change — let LLM decide (could be a miss-click)
        return None

    # navigate: the `open` subprocess either raises (caught by executor) or
    # succeeds synchronously.  If we reach verification the command ran OK;
    # the page may still be loading but that is handled by the loading loop.
    if action_type == "navigate":
        return {
            "success": True,
            "explanation": "navigate executed; browser is loading the URL.",
            "task_complete": False,
            "confidence": "high",
            "screen_changed": screen_changed,
        }

    # select_all, form_fill, file_select, window_switch, drag: let LLM verify
    return None
