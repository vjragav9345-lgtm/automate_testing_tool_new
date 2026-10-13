"""Pixel-diff comparison between a baseline screenshot and what a run produced.

Nothing fancy - resize to match, sum the pixel delta, compare against a
threshold. Good enough to catch a badly broken layout, not meant to be a
perceptual diff tool.
"""
import logging
from pathlib import Path

from PIL import Image, ImageChops

from storage.repository import BASE_DIR

logger = logging.getLogger(__name__)

DEFAULT_THRESHOLD = 0.02  # fraction of max possible pixel difference


def _resolve(path_str):
    p = Path(path_str)
    if p.is_absolute() and p.exists():
        return p
    candidate = BASE_DIR / path_str
    return candidate if candidate.exists() else None


def compare_screenshots(expected_path, actual_path, threshold=DEFAULT_THRESHOLD):
    if not expected_path:
        return None

    expected_full = _resolve(expected_path)
    if expected_full is None:
        # baseline missing shouldn't kill the run, just note it and move on
        return {"match": None, "diff_ratio": None, "note": f"baseline screenshot not found at {expected_path}, skipped"}

    if not actual_path:
        return {"match": None, "diff_ratio": None, "note": "no screenshot was captured from the run to compare"}

    actual_full = BASE_DIR / actual_path
    if not actual_full.exists():
        return {"match": None, "diff_ratio": None, "note": "run screenshot missing on disk, skipped"}

    try:
        img_a = Image.open(expected_full).convert("RGB")
        img_b = Image.open(actual_full).convert("RGB")
    except Exception as e:
        logger.warning("couldn't open screenshots for diff: %s", e)
        return {"match": None, "diff_ratio": None, "note": f"couldn't open screenshots: {e}"}

    if img_a.size != img_b.size:
        img_b = img_b.resize(img_a.size)

    diff = ImageChops.difference(img_a, img_b)
    hist = diff.histogram()
    total_channel_values = img_a.size[0] * img_a.size[1] * 3
    diff_sum = sum(i * count for i, count in enumerate(hist))
    diff_ratio = diff_sum / (total_channel_values * 255)

    return {
        "match": diff_ratio <= threshold,
        "diff_ratio": round(diff_ratio, 4),
        "note": None,
    }
