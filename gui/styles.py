"""Color palette and QSS stylesheet for the Vercept desktop app.

Color story: warm cream background with peach accents and near-black typography.
The palette is intentionally warm and analog-feeling — not cold tech-blue.
"""

# ── Palette ─────────────────────────────────────────────────────────────────

CREAM       = "#FFF8F0"   # main background
PEACH_LIGHT = "#FFF0E6"   # card / panel backgrounds
PEACH_MID   = "#F5D9C4"   # borders, dividers
PEACH_DARK  = "#E8C4A8"   # stronger borders, inactive states
PEACH_HOT   = "#D4956A"   # accent / highlight
BLACK       = "#1A1A1A"   # primary text, buttons
GRAY_DARK   = "#444444"   # secondary text
GRAY_MID    = "#888888"   # labels, placeholders
GRAY_LIGHT  = "#BBBBBB"   # disabled states
WHITE       = "#FFFFFF"   # input backgrounds
SUCCESS     = "#2D8B5A"   # action succeeded
ERROR       = "#B5332A"   # action failed / aborted
RUNNING     = "#C47F35"   # in-progress amber
INFO        = "#4A6FA5"   # informational blue-gray

# ── Full application stylesheet ──────────────────────────────────────────────

STYLESHEET = f"""

/* ── Base ──────────────────────────────────────────────────────────────── */

QMainWindow, QDialog {{
    background-color: {CREAM};
}}

QWidget {{
    background-color: {CREAM};
    color: {BLACK};
    font-size: 13px;
}}

/* ── Task input ─────────────────────────────────────────────────────────── */

#task_input {{
    background-color: {WHITE};
    border: 1.5px solid {PEACH_DARK};
    border-radius: 10px;
    padding: 10px 14px;
    font-size: 14px;
    color: {BLACK};
    selection-background-color: {PEACH_MID};
    line-height: 1.5;
}}

#task_input:focus {{
    border-color: {PEACH_HOT};
}}

/* ── Buttons ────────────────────────────────────────────────────────────── */

#run_button {{
    background-color: {BLACK};
    color: {WHITE};
    border: none;
    border-radius: 8px;
    padding: 10px 0px;
    font-size: 13px;
    font-weight: 600;
    letter-spacing: 0.2px;
}}

#run_button:hover {{
    background-color: #333333;
}}

#run_button:pressed {{
    background-color: #000000;
}}

#run_button:disabled {{
    background-color: {GRAY_LIGHT};
    color: {WHITE};
}}

#stop_button {{
    background-color: transparent;
    color: {GRAY_DARK};
    border: 1.5px solid {PEACH_DARK};
    border-radius: 8px;
    padding: 10px 0px;
    font-size: 13px;
    font-weight: 500;
}}

#stop_button:hover {{
    background-color: {PEACH_LIGHT};
    border-color: {PEACH_HOT};
    color: {BLACK};
}}

#stop_button:disabled {{
    color: {GRAY_LIGHT};
    border-color: {PEACH_MID};
}}

/* ── Cards / panels ─────────────────────────────────────────────────────── */

#task_card, #activity_card {{
    background-color: {PEACH_LIGHT};
    border: 1px solid {PEACH_MID};
    border-radius: 12px;
}}

#preview_card {{
    background-color: {BLACK};
    border-radius: 14px;
}}

/* ── Labels ─────────────────────────────────────────────────────────────── */

#section_label {{
    color: {GRAY_MID};
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1.2px;
}}

#status_label {{
    color: {GRAY_DARK};
    font-size: 12px;
}}

#app_name_label {{
    color: {GRAY_MID};
    font-size: 11px;
}}

#title_label {{
    color: {BLACK};
    font-size: 18px;
    font-weight: 700;
    letter-spacing: -0.3px;
}}

/* ── Log scroll area ────────────────────────────────────────────────────── */

#log_scroll {{
    background-color: transparent;
    border: none;
}}

#log_scroll QScrollBar:vertical {{
    background: transparent;
    width: 5px;
    margin: 2px 0;
}}

#log_scroll QScrollBar::handle:vertical {{
    background: {PEACH_DARK};
    border-radius: 2px;
    min-height: 20px;
}}

#log_scroll QScrollBar::handle:vertical:hover {{
    background: {PEACH_HOT};
}}

#log_scroll QScrollBar::add-line:vertical,
#log_scroll QScrollBar::sub-line:vertical {{
    height: 0;
}}

/* ── Horizontal divider ─────────────────────────────────────────────────── */

#divider {{
    background-color: {PEACH_MID};
    max-height: 1px;
    border: none;
}}

/* ── Status pill ────────────────────────────────────────────────────────── */

#status_pill {{
    border-radius: 10px;
    padding: 3px 10px;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.3px;
}}

"""
