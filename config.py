from dataclasses import dataclass, field
import os

from dotenv import load_dotenv


@dataclass
class VerceptConfig:
    openai_api_key: str
    model: str = "gpt-4o"
    screenshot_scale: float = 0.5
    action_delay: float = 0.5
    max_actions_per_task: int = 50
    max_retries: int = 3
    confirmation_required: bool = True
    ocr_enabled: bool = True
    dry_run: bool = False

    # Timeouts
    max_task_duration: int = 1800  # 30 minutes per task
    action_timeout: int = 30  # seconds per action

    # Safety: app restrictions (macOS)
    app_blacklist: list[str] = field(default_factory=lambda: [
        "System Preferences",
        "System Settings",
        "Keychain Access",
        "Passwords",
    ])
    app_whitelist: list[str] | None = None  # If set, ONLY these apps are allowed

    # Safety: file operations
    confirm_file_operations: bool = True

    # Audit logging
    enable_audit_logging: bool = True
    audit_log_path: str = "~/.vercept/audit.log"

    # Session persistence
    session_storage_enabled: bool = True
    session_dir: str = "~/.vercept/sessions"

    # Perception tuning
    change_detection_threshold: float = 0.02  # 2% pixel diff = "significant"

    # Execution tuning
    key_press_delay: float = 0.05  # delay between key presses
    file_dialog_timeout: float = 5.0  # seconds to wait for file dialog


def load_config() -> VerceptConfig:
    load_dotenv()
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit(
            "Error: OPENAI_API_KEY not found. "
            "Set it in a .env file or as an environment variable."
        )
    return VerceptConfig(
        openai_api_key=api_key,
        dry_run=os.environ.get("VERCEPT_DRY_RUN", "").lower() in ("1", "true"),
    )
