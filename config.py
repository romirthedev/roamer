from dataclasses import dataclass
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
