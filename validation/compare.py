"""Pixel-diff comparison between a baseline screenshot and what a run produced.

Nothing fancy - resize to match, sum the pixel delta, compare against a
threshold. Good enough to catch a badly broken layout, not meant to be a
perceptual diff tool. Still true with the additions below - no AI/vision
service, no perceptual hashing, just the same deterministic pixel-sum
diff, with two purely mechanical ways to keep it from tripping on content
that's expected to vary run-to-run:

  - ignored_regions: rectangles (in the BASELINE image's own pixel
    coordinates) blacked out on both images identically before diffing -
    for a timestamp, an ad slot, a "Welcome, <name>" banner, or any other
    region that's known in advance to legitimately differ every run.
  - per-pixel noise floor: a channel difference this small or smaller
    is treated as 0 before summing - anti-aliasing/
    sub-pixel font rendering differences between two otherwise-identical
    screenshots are usually single-digit per-channel deltas spread across
    many pixels, which the OLD sum-everything approach counted in full;
    this is what "small rendering differences" in the caller's own
    docstring refers to. A genuinely different pixel (different color
    entirely) is nowhere near this small and is completely unaffected.

ignored_regions is always opt-in (empty by default - nothing is masked
unless the caller names a region). The per-pixel noise floor is on by
default at a small, conservative value (just enough to absorb ordinary
anti-aliasing noise, nowhere near enough to hide a real visual change);
pass strict=True for the exact original behavior (every nonzero pixel
delta counts, in full) when that's specifically what's wanted.
"""
import logging
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageStat

from storage.repository import BASE_DIR

logger = logging.getLogger(__name__)

DEFAULT_THRESHOLD = 0.02  # fraction of max possible pixel difference

# per-channel difference (0-255) at or below this is treated as noise, not
# a real visual difference, UNLESS strict=True is passed. Small enough
# that an actually-different pixel (a different color swatch, a shifted
# element revealing what was behind it, ...) is essentially never this
# close - typical anti-aliasing/font-hinting deltas between two renders
# of the identical page are usually under 10 per channel.
DEFAULT_PIXEL_NOISE_FLOOR = 8


def _resolve(path_str):
    p = Path(path_str)
    if p.is_absolute() and p.exists():
        return p
    candidate = BASE_DIR / path_str
    return candidate if candidate.exists() else None


def _mask_regions(img, regions):
    """Returns a COPY of img with each region blacked out - never mutates
    the caller's own Image object, since the same regions get applied to
    both images being compared and each must see its own original pixels
    everywhere outside the masked rectangles.
    """
    if not regions:
        return img
    masked = img.copy()
    draw = ImageDraw.Draw(masked)
    w, h = masked.size
    for region in regions:
        try:
            x = max(0, int(region.get("x", 0)))
            y = max(0, int(region.get("y", 0)))
            rw = int(region.get("width", 0))
            rh = int(region.get("height", 0))
        except (TypeError, ValueError):
            continue
        if rw <= 0 or rh <= 0:
            continue
        x2 = min(w, x + rw)
        y2 = min(h, y + rh)
        if x >= x2 or y >= y2:
            continue
        draw.rectangle([x, y, x2 - 1, y2 - 1], fill=(0, 0, 0))
    return masked


def compare_screenshots(expected_path, actual_path, threshold=DEFAULT_THRESHOLD, ignored_regions=None, strict=False):
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
        # raw PIL/file error stays in the backend log only - "note" is
        # surfaced to the user (e.g. in the report's screenshot section)
        logger.warning("couldn't open screenshots for diff: %s", e)
        return {"match": None, "diff_ratio": None, "note": "couldn't open one of the screenshots to compare"}

    if img_a.size != img_b.size:
        img_b = img_b.resize(img_a.size)

    if ignored_regions:
        img_a = _mask_regions(img_a, ignored_regions)
        img_b = _mask_regions(img_b, ignored_regions)

    diff = ImageChops.difference(img_a, img_b)

    noise_floor = 0 if strict else DEFAULT_PIXEL_NOISE_FLOOR
    if noise_floor > 0:
        # zeroes out every per-channel delta at or below the noise floor
        # before summing - point() applies a 256-entry lookup table to
        # every pixel/channel, so this is one cheap, vectorized pass, not
        # a per-pixel Python loop
        lut = [0 if v <= noise_floor else v for v in range(256)] * 3
        diff = diff.point(lut)

    # REAL BUG FIX (found while testing this module for the improvements
    # above - reproduced with two byte-identical images and confirmed the
    # existing code, unchanged, reported diff_ratio > 1.0 for them): a
    # multi-band (RGB) image's .histogram() returns ONE list, the three
    # bands' 256-bin histograms simply concatenated end to end (indices
    # 0-255 = R, 256-511 = G, 512-767 = B) - not three separate 0-255
    # histograms. The old `sum(i * count for i, count in enumerate(hist))`
    # used the raw 0-767 index as if it were a pixel value for every band,
    # so the G band's "no difference" bin (all pixels, at index 256) alone
    # contributed 256 * (width*height) to diff_sum, and B's contributed
    # 512 * (width*height) - meaning even two IDENTICAL screenshots never
    # produced a zero (or even a small) diff_ratio. ImageStat.Stat(diff)
    # .sum gives the correct sum of pixel VALUES per band directly (a
    # 3-element list, one true sum per band) - no index/bin confusion
    # possible, and it's what the original code's own naming (diff_sum)
    # was clearly trying to compute.
    stat = ImageStat.Stat(diff)
    diff_sum = sum(stat.sum)
    total_channel_values = img_a.size[0] * img_a.size[1] * 3
    diff_ratio = diff_sum / (total_channel_values * 255)

    return {
        "match": diff_ratio <= threshold,
        "diff_ratio": round(diff_ratio, 4),
        "note": None,
    }
