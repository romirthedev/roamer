import base64
import io
import json
import time
from dataclasses import dataclass, field

import pyautogui
import pytesseract
from openai import OpenAI
from PIL import Image

from config import VerceptConfig
from vercept.prompts import PERCEIVE_PROMPT


@dataclass
class ScreenState:
    screenshot_base64: str
    timestamp: float
    ocr_text: str
    description: str
    elements: list[dict] = field(default_factory=list)
    errors: str = ""
    active_app: str = ""
    screen_width: int = 0
    screen_height: int = 0
    # Original (pre-scale) dimensions for coordinate mapping
    original_width: int = 0
    original_height: int = 0


class Perception:
    def __init__(self, config: VerceptConfig):
        self.config = config
        self.client = OpenAI(api_key=config.openai_api_key)

    def capture(self) -> ScreenState:
        image = self._take_screenshot()
        original_w, original_h = image.size

        scaled = self._scale_image(image)
        scaled_w, scaled_h = scaled.size

        screenshot_b64 = self._image_to_base64(scaled)

        ocr_text = ""
        if self.config.ocr_enabled:
            ocr_text = self._run_ocr(image)

        analysis = self._analyze_with_vlm(screenshot_b64, scaled_w, scaled_h)

        return ScreenState(
            screenshot_base64=screenshot_b64,
            timestamp=time.time(),
            ocr_text=ocr_text,
            description=analysis.get("description", ""),
            elements=analysis.get("elements", []),
            errors=analysis.get("errors", ""),
            active_app=analysis.get("active_app", ""),
            screen_width=scaled_w,
            screen_height=scaled_h,
            original_width=original_w,
            original_height=original_h,
        )

    def _take_screenshot(self) -> Image.Image:
        screenshot = pyautogui.screenshot()
        return screenshot

    def _scale_image(self, image: Image.Image) -> Image.Image:
        scale = self.config.screenshot_scale
        if scale >= 1.0:
            return image
        new_w = int(image.width * scale)
        new_h = int(image.height * scale)
        return image.resize((new_w, new_h), Image.LANCZOS)

    def _image_to_base64(self, image: Image.Image) -> str:
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode("utf-8")

    def _run_ocr(self, image: Image.Image) -> str:
        try:
            return pytesseract.image_to_string(image).strip()
        except Exception:
            return ""

    def _analyze_with_vlm(
        self, screenshot_b64: str, width: int, height: int
    ) -> dict:
        prompt = PERCEIVE_PROMPT.format(width=width, height=height)
        try:
            response = self.client.chat.completions.create(
                model=self.config.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{screenshot_b64}",
                                    "detail": "high",
                                },
                            },
                        ],
                    }
                ],
                max_tokens=2000,
                temperature=0,
            )
            raw = response.choices[0].message.content.strip()
            # Strip markdown fences if the model adds them
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
                if raw.endswith("```"):
                    raw = raw[:-3]
                raw = raw.strip()
            return json.loads(raw)
        except (json.JSONDecodeError, Exception) as e:
            return {
                "description": f"VLM analysis failed: {e}",
                "elements": [],
                "errors": str(e),
                "active_app": "",
            }
