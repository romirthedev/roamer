"""Background QThread that runs the Vercept agent and forwards events to the GUI."""

from PyQt6.QtCore import QThread, pyqtSignal


class AgentWorker(QThread):
    """Runs Agent.run() on a background thread.

    The agent's on_event callback is wired to emit `event_signal`, which the
    main window connects to its `on_agent_event` slot.  Qt's signal/slot
    mechanism handles the thread-boundary crossing safely.
    """

    event_signal = pyqtSignal(dict)
    finished_signal = pyqtSignal()
    error_signal = pyqtSignal(str)

    def __init__(self, instruction: str, parent=None):
        super().__init__(parent)
        self.instruction = instruction
        self._agent = None

    def run(self):
        try:
            # Import here so the heavy deps (openai, pyautogui, PIL) are loaded
            # lazily — the GUI stays snappy even before the first task runs.
            from config import load_config
            from vercept.agent import Agent

            config = load_config()
            self._agent = Agent(config, on_event=self.event_signal.emit)
            self._agent.run(self.instruction)
        except SystemExit as e:
            self.error_signal.emit(str(e))
        except Exception as e:
            self.error_signal.emit(f"Unexpected error: {e}")
        finally:
            self.finished_signal.emit()

    def stop(self):
        """Request a graceful stop; force-terminate after a timeout."""
        if self._agent is not None:
            self._agent.request_stop()
        # Give the agent up to 6 s to finish its current action before
        # force-terminating the thread.
        if not self.wait(6000):
            self.terminate()
            self.wait()
