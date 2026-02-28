#!/usr/bin/env python3
"""Launch the Vercept desktop app.

Usage:
    python main_gui.py

Requirements:
    pip install PyQt6
    (All other requirements are the same as the CLI version.)
"""

import sys

try:
    from gui.app import run_app
except ImportError as e:
    print(f"Error: {e}")
    print("Install the GUI dependencies with:  pip install PyQt6")
    sys.exit(1)

if __name__ == "__main__":
    sys.exit(run_app())
