"""Screen change detection between consecutive captures."""

import base64
import io

from PIL import Image, ImageChops


def compare_screens(before_b64: str, after_b64: str, threshold: float = 0.02) -> dict:
    """Compare two screenshots and return change information.

    Args:
        before_b64: Base64-encoded PNG of the before screenshot.
        after_b64: Base64-encoded PNG of the after screenshot.
        threshold: Fraction of pixels that must differ to count as "significant".

    Returns:
        dict with keys:
            changed: bool — whether the screen changed significantly
            diff_ratio: float — fraction of pixels that differ
            changed_regions: list of {x, y, width, height} bounding boxes
    """
    try:
        before_img = _b64_to_image(before_b64)
        after_img = _b64_to_image(after_b64)
    except Exception:
        return {"changed": True, "diff_ratio": 1.0, "changed_regions": []}

    if before_img.size != after_img.size:
        return {"changed": True, "diff_ratio": 1.0, "changed_regions": []}

    diff = ImageChops.difference(before_img.convert("RGB"), after_img.convert("RGB"))
    pixels = list(diff.getdata())
    total = len(pixels)
    changed_count = sum(1 for r, g, b in pixels if r + g + b > 30)
    diff_ratio = changed_count / total if total > 0 else 0.0
    changed = diff_ratio > threshold

    changed_regions = []
    if changed:
        changed_regions = _find_changed_regions(diff)

    return {
        "changed": changed,
        "diff_ratio": round(diff_ratio, 4),
        "changed_regions": changed_regions,
    }


def _b64_to_image(b64_str: str) -> Image.Image:
    data = base64.b64decode(b64_str)
    return Image.open(io.BytesIO(data))


def _find_changed_regions(diff_image: Image.Image) -> list[dict]:
    """Find bounding boxes of changed regions by dividing screen into a grid."""
    width, height = diff_image.size
    grid_cols = 4
    grid_rows = 4
    cell_w = width // grid_cols
    cell_h = height // grid_rows

    regions = []
    for row in range(grid_rows):
        for col in range(grid_cols):
            x0 = col * cell_w
            y0 = row * cell_h
            x1 = x0 + cell_w
            y1 = y0 + cell_h
            cell = diff_image.crop((x0, y0, x1, y1))
            cell_pixels = list(cell.getdata())
            changed = sum(1 for r, g, b in cell_pixels if r + g + b > 30)
            if changed / len(cell_pixels) > 0.01:
                regions.append({
                    "x": x0,
                    "y": y0,
                    "width": cell_w,
                    "height": cell_h,
                })

    return regions
