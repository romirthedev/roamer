"""Vercept main application window."""

import base64
import time

from PyQt6.QtCore import Qt, QSize, pyqtSlot
from PyQt6.QtGui import QPixmap, QColor, QPainter, QBrush, QPen, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QPlainTextEdit, QPushButton, QScrollArea,
    QFrame, QSizePolicy, QSpacerItem,
)

from gui.styles import (
    STYLESHEET,
    CREAM, PEACH_LIGHT, PEACH_MID, PEACH_DARK, PEACH_HOT,
    BLACK, GRAY_DARK, GRAY_MID, GRAY_LIGHT, WHITE,
    SUCCESS, ERROR, RUNNING, INFO,
)
from gui.worker import AgentWorker


# ── Screen preview widget ────────────────────────────────────────────────────

class ScreenPreview(QLabel):
    """Displays the agent's current screenshot, scaled to fit while keeping
    aspect ratio.  Shows a placeholder when no image is available."""

    _PLACEHOLDER_TEXT = "Screen preview\nwill appear here"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pixmap_raw: QPixmap | None = None
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(300, 200)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        self.setText(self._PLACEHOLDER_TEXT)
        self.setStyleSheet(f"color: {GRAY_MID}; font-size: 13px;")

    def set_screenshot_b64(self, b64: str) -> None:
        data = base64.b64decode(b64)
        pixmap = QPixmap()
        pixmap.loadFromData(data)
        self._pixmap_raw = pixmap
        self.setText("")
        self._refresh()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._refresh()

    def _refresh(self):
        if self._pixmap_raw and not self._pixmap_raw.isNull():
            scaled = self._pixmap_raw.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            super().setPixmap(scaled)


# ── Activity log entry ───────────────────────────────────────────────────────

class LogEntry(QFrame):
    """A single row in the activity log.

    Displays a coloured status icon, the action type in bold, and a detail
    line.  The status can be updated in-place when verification arrives.
    """

    # Status constants
    PENDING  = "pending"
    SUCCESS  = "success"
    FAILURE  = "failure"
    INFO     = "info"

    _DOT_COLORS = {
        "pending": RUNNING,
        "success": SUCCESS,
        "failure": ERROR,
        "info":    GRAY_MID,
    }
    _DOT_CHARS = {
        "pending": "●",
        "success": "✓",
        "failure": "✗",
        "info":    "·",
    }

    def __init__(self, action_type: str, detail: str, status: str = "pending", parent=None):
        super().__init__(parent)
        self.setObjectName("log_entry")
        self.setStyleSheet(
            f"QFrame#log_entry {{ background-color: transparent; border: none; }}"
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(8)

        # Status dot
        self._dot = QLabel(self._DOT_CHARS[status])
        self._dot.setFixedWidth(16)
        self._dot.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        self._dot.setStyleSheet(
            f"color: {self._DOT_COLORS[status]}; font-size: 14px; font-weight: bold;"
            "padding-top: 1px;"
        )
        layout.addWidget(self._dot)

        # Text column
        text_col = QVBoxLayout()
        text_col.setSpacing(1)
        text_col.setContentsMargins(0, 0, 0, 0)

        self._title = QLabel(action_type)
        self._title.setStyleSheet(
            f"color: {BLACK}; font-weight: 600; font-size: 12px; background: transparent;"
        )
        text_col.addWidget(self._title)

        self._detail = QLabel(detail)
        self._detail.setStyleSheet(
            f"color: {GRAY_DARK}; font-size: 11px; background: transparent;"
        )
        self._detail.setWordWrap(True)
        text_col.addWidget(self._detail)

        layout.addLayout(text_col)
        layout.addStretch()

    def update_status(self, status: str, detail: str = "") -> None:
        self._dot.setText(self._DOT_CHARS.get(status, "·"))
        self._dot.setStyleSheet(
            f"color: {self._DOT_COLORS.get(status, GRAY_MID)}; font-size: 14px; "
            "font-weight: bold; padding-top: 1px;"
        )
        if detail:
            self._detail.setText(detail)


# ── Status pill ──────────────────────────────────────────────────────────────

class StatusPill(QLabel):
    """Rounded pill label that shows the agent's current state."""

    _STYLES = {
        "idle":     (PEACH_MID,    GRAY_DARK,  "Ready"),
        "running":  (RUNNING,      WHITE,      "Running"),
        "planning": (RUNNING,      WHITE,      "Planning…"),
        "complete": (SUCCESS,      WHITE,      "Complete"),
        "stopped":  (GRAY_LIGHT,   GRAY_DARK,  "Stopped"),
        "error":    (ERROR,        WHITE,      "Error"),
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("status_pill")
        self.set_state("idle")

    def set_state(self, state: str) -> None:
        bg, fg, text = self._STYLES.get(state, self._STYLES["idle"])
        self.setText(text)
        self.setStyleSheet(
            f"QLabel#status_pill {{ "
            f"  background-color: {bg}; color: {fg}; "
            f"  border-radius: 10px; padding: 3px 10px; "
            f"  font-size: 11px; font-weight: 600; letter-spacing: 0.3px; "
            f"}}"
        )


# ── Main window ──────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):

    # How many log entries to keep before pruning the oldest
    MAX_LOG_ENTRIES = 80

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Vercept")
        self.setMinimumSize(1000, 680)
        self.resize(1160, 760)

        self._worker: AgentWorker | None = None
        # Maps action_number → LogEntry so we can update it when verification arrives
        self._pending_entries: dict[int, LogEntry] = {}
        self._current_action_number = 0
        self._log_entries: list[LogEntry] = []

        self.setStyleSheet(STYLESHEET)
        self._build_ui()
        self._wire_shortcuts()

    # ── UI construction ──────────────────────────────────────────────────────

    def _build_ui(self):
        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)

        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # ── Header bar ───────────────────────────────────────────────────────
        header = QWidget()
        header.setFixedHeight(52)
        header.setStyleSheet(f"background-color: {CREAM}; border-bottom: 1px solid {PEACH_MID};")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 0, 20, 0)

        title = QLabel("Vercept")
        title.setObjectName("title_label")
        header_layout.addWidget(title)
        header_layout.addStretch()

        self._status_pill = StatusPill()
        header_layout.addWidget(self._status_pill)

        self._app_label = QLabel("")
        self._app_label.setObjectName("app_name_label")
        header_layout.addWidget(self._app_label)

        root_layout.addWidget(header)

        # ── Content area ─────────────────────────────────────────────────────
        content = QWidget()
        content_layout = QHBoxLayout(content)
        content_layout.setContentsMargins(16, 16, 16, 16)
        content_layout.setSpacing(14)

        # Left: screen preview (60% width)
        left = QWidget()
        left.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)

        preview_card = QFrame()
        preview_card.setObjectName("preview_card")
        preview_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        preview_card_layout = QVBoxLayout(preview_card)
        preview_card_layout.setContentsMargins(6, 6, 6, 6)

        self._preview = ScreenPreview()
        preview_card_layout.addWidget(self._preview)
        left_layout.addWidget(preview_card, stretch=1)

        # Caption below preview
        self._preview_caption = QLabel("No task running")
        self._preview_caption.setObjectName("status_label")
        self._preview_caption.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview_caption.setStyleSheet(
            f"color: {GRAY_MID}; font-size: 11px; padding: 2px 0;"
        )
        left_layout.addWidget(self._preview_caption)

        content_layout.addWidget(left, stretch=60)

        # Right: controls + log (40% width)
        right = QWidget()
        right.setFixedWidth(360)
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(12)

        # Task card
        task_card = QFrame()
        task_card.setObjectName("task_card")
        task_card_layout = QVBoxLayout(task_card)
        task_card_layout.setContentsMargins(16, 14, 16, 14)
        task_card_layout.setSpacing(10)

        task_label = QLabel("TASK")
        task_label.setObjectName("section_label")
        task_card_layout.addWidget(task_label)

        self._task_input = QPlainTextEdit()
        self._task_input.setObjectName("task_input")
        self._task_input.setPlaceholderText(
            "What would you like to do?\n\nTip: Cmd+Return to run"
        )
        self._task_input.setFixedHeight(80)
        task_card_layout.addWidget(self._task_input)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self._run_btn = QPushButton("Run Task")
        self._run_btn.setObjectName("run_button")
        self._run_btn.setFixedHeight(38)
        self._run_btn.clicked.connect(self._on_run)

        self._stop_btn = QPushButton("Stop")
        self._stop_btn.setObjectName("stop_button")
        self._stop_btn.setFixedHeight(38)
        self._stop_btn.setFixedWidth(80)
        self._stop_btn.setEnabled(False)
        self._stop_btn.clicked.connect(self._on_stop)

        btn_row.addWidget(self._run_btn, stretch=1)
        btn_row.addWidget(self._stop_btn)
        task_card_layout.addLayout(btn_row)

        right_layout.addWidget(task_card)

        # Activity card
        activity_card = QFrame()
        activity_card.setObjectName("activity_card")
        activity_card.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Expanding,
        )
        activity_layout = QVBoxLayout(activity_card)
        activity_layout.setContentsMargins(16, 14, 16, 14)
        activity_layout.setSpacing(8)

        activity_header = QLabel("ACTIVITY")
        activity_header.setObjectName("section_label")
        activity_layout.addWidget(activity_header)

        # Scroll area for log entries
        self._log_scroll = QScrollArea()
        self._log_scroll.setObjectName("log_scroll")
        self._log_scroll.setWidgetResizable(True)
        self._log_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._log_widget = QWidget()
        self._log_widget.setStyleSheet("background: transparent;")
        self._log_layout = QVBoxLayout(self._log_widget)
        self._log_layout.setContentsMargins(0, 0, 4, 0)
        self._log_layout.setSpacing(0)
        self._log_layout.addStretch()  # pushes entries to the top initially

        self._log_scroll.setWidget(self._log_widget)
        activity_layout.addWidget(self._log_scroll)

        right_layout.addWidget(activity_card, stretch=1)

        content_layout.addWidget(right, stretch=40)

        root_layout.addWidget(content, stretch=1)

    def _wire_shortcuts(self):
        # Cmd+Return to run task from anywhere in the window
        shortcut = QShortcut(QKeySequence("Ctrl+Return"), self)
        shortcut.activated.connect(self._on_run)
        # macOS Cmd+Return
        shortcut2 = QShortcut(QKeySequence("Meta+Return"), self)
        shortcut2.activated.connect(self._on_run)

    # ── Log helpers ──────────────────────────────────────────────────────────

    def _add_log_entry(
        self,
        action_type: str,
        detail: str,
        status: str = LogEntry.PENDING,
        action_number: int = 0,
    ) -> LogEntry:
        """Append a new entry and optionally register it for later update."""
        # Prune if too many entries
        if len(self._log_entries) >= self.MAX_LOG_ENTRIES:
            oldest = self._log_entries.pop(0)
            self._log_layout.removeWidget(oldest)
            oldest.deleteLater()

        entry = LogEntry(action_type, detail, status)
        # Insert before the trailing stretch (last item)
        count = self._log_layout.count()
        self._log_layout.insertWidget(count - 1, entry)
        self._log_entries.append(entry)

        if action_number:
            self._pending_entries[action_number] = entry

        self._scroll_log_to_bottom()
        return entry

    def _add_separator(self):
        """Add a thin horizontal line between task runs."""
        sep = QFrame()
        sep.setObjectName("divider")
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background-color: {PEACH_DARK}; border: none;")
        count = self._log_layout.count()
        self._log_layout.insertWidget(count - 1, sep)
        self._log_entries.append(sep)

    def _scroll_log_to_bottom(self):
        sb = self._log_scroll.verticalScrollBar()
        if sb:
            sb.setValue(sb.maximum())

    def _clear_log(self):
        for entry in self._log_entries:
            self._log_layout.removeWidget(entry)
            entry.deleteLater()
        self._log_entries.clear()
        self._pending_entries.clear()

    # ── Button handlers ──────────────────────────────────────────────────────

    def _on_run(self):
        instruction = self._task_input.toPlainText().strip()
        if not instruction:
            self._task_input.setFocus()
            return
        if self._worker and self._worker.isRunning():
            return

        self._set_running_state(True)
        self._status_pill.set_state("running")
        self._preview_caption.setText("Running…")
        self._current_action_number = 0
        self._pending_entries.clear()

        # Add a session header to the log
        self._add_log_entry(
            instruction[:60] + ("…" if len(instruction) > 60 else ""),
            time.strftime("%H:%M:%S"),
            LogEntry.INFO,
        )

        self._worker = AgentWorker(instruction, parent=self)
        self._worker.event_signal.connect(self.on_agent_event)
        self._worker.finished_signal.connect(self._on_worker_finished)
        self._worker.error_signal.connect(self._on_worker_error)
        self._worker.start()

    def _on_stop(self):
        if self._worker and self._worker.isRunning():
            self._stop_btn.setEnabled(False)
            self._stop_btn.setText("Stopping…")
            self._worker.stop()

    def _on_worker_finished(self):
        self._set_running_state(False)
        if self._status_pill._DOT_CHARS:  # just check it's alive
            pass
        self._add_separator()

    def _on_worker_error(self, message: str):
        self._add_log_entry("Error", message, LogEntry.FAILURE)
        self._status_pill.set_state("error")
        self._set_running_state(False)

    def _set_running_state(self, running: bool):
        self._run_btn.setEnabled(not running)
        self._stop_btn.setEnabled(running)
        self._stop_btn.setText("Stop")
        self._task_input.setReadOnly(running)

    # ── Agent event handler ──────────────────────────────────────────────────

    @pyqtSlot(dict)
    def on_agent_event(self, event: dict):
        """Dispatch agent events to UI updates.  Always called on the main thread
        thanks to Qt's cross-thread signal delivery."""
        etype = event.get("type", "")

        if etype == "screen":
            b64 = event.get("screenshot_b64", "")
            if b64:
                self._preview.set_screenshot_b64(b64)
            app = event.get("app", "")
            if app:
                self._app_label.setText(app)
            description = event.get("description", "")
            if description:
                self._preview_caption.setText(description[:80])

        elif etype == "planning":
            self._status_pill.set_state("planning")

        elif etype == "action_planned":
            action_type = event.get("action_type", "action")
            reasoning = event.get("reasoning", "")
            confidence = event.get("confidence", "high")
            action_number = event.get("action_number", 0)
            self._current_action_number = action_number

            conf_suffix = "" if confidence == "high" else f" [{confidence}]"
            self._add_log_entry(
                action_type + conf_suffix,
                reasoning[:100] if reasoning else "",
                LogEntry.PENDING,
                action_number=action_number,
            )
            self._status_pill.set_state("running")

        elif etype == "action_executed":
            result = event.get("result", "")
            # If the result looks like an error, update the pending entry
            num = self._current_action_number
            if num in self._pending_entries:
                entry = self._pending_entries[num]
                if result.startswith(("execution_error", "unknown_action")):
                    entry.update_status(LogEntry.FAILURE, result)

        elif etype == "verified":
            success = event.get("success", True)
            explanation = event.get("explanation", "")
            num = self._current_action_number
            if num in self._pending_entries:
                status = LogEntry.SUCCESS if success else LogEntry.FAILURE
                self._pending_entries[num].update_status(status, explanation[:100])
                del self._pending_entries[num]

        elif etype == "task_complete":
            summary = event.get("summary", "Task completed.")
            self._add_log_entry("Complete", summary[:120], LogEntry.SUCCESS)
            self._status_pill.set_state("complete")
            self._preview_caption.setText("Task complete")

        elif etype == "task_aborted":
            reason = event.get("reason", "Aborted.")
            self._add_log_entry("Aborted", reason[:120], LogEntry.FAILURE)
            self._status_pill.set_state("error")
            self._preview_caption.setText("Task aborted")

        elif etype == "stopped":
            self._add_log_entry("Stopped", "Task stopped by user.", LogEntry.INFO)
            self._status_pill.set_state("stopped")
            self._preview_caption.setText("Stopped")

        elif etype == "loading":
            self._preview_caption.setText("Loading…")

        elif etype == "log":
            level = event.get("level", "info")
            message = event.get("message", "")
            status = LogEntry.FAILURE if level == "error" else LogEntry.INFO
            self._add_log_entry("⚠", message[:100], status)
