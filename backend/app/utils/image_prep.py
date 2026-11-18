"""Prepare photos of handwritten documents so the vision model can read them.

OpenAI's high-detail mode scales every image so its short side is at most 768 px. A tall phone photo of a
prescription therefore loses most of its pixels, and small handwriting becomes unreadable. We fix that by sending
the full page (for layout) plus overlapping zoomed-in strips (for detail), after fixing rotation and contrast.
"""
import io
import logging

from PIL import Image, ImageOps, UnidentifiedImageError

logger = logging.getLogger("ai")

MAX_SIDE = 2048         # OpenAI downsizes anything larger anyway
STRIP_ASPECT = 1.3      # only split images whose long side is this much longer than the short side
STRIP_OVERLAP = 0.18    # strips overlap so a line of writing is never cut in half


def _encode(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=92)
    return buf.getvalue()


def _fit(img: Image.Image) -> Image.Image:
    img = img.copy()
    img.thumbnail((MAX_SIDE, MAX_SIDE), Image.LANCZOS)
    return img


def _strips(img: Image.Image) -> list[Image.Image]:
    """Split along the long side into near-square, overlapping pieces."""
    w, h = img.size
    long_side, short_side = max(w, h), min(w, h)
    if long_side < short_side * STRIP_ASPECT:
        return []
    count = max(2, round(long_side / short_side + 0.5))
    size = int(long_side / (count - (count - 1) * STRIP_OVERLAP))
    step = int(size * (1 - STRIP_OVERLAP))
    pieces = []
    for i in range(count):
        start = min(i * step, long_side - size)
        box = (0, start, w, start + size) if h >= w else (start, 0, start + size, h)
        pieces.append(img.crop(box))
    return pieces


def prepare_image(content: bytes) -> tuple[list[bytes], str]:
    """Return ([full page, *zoomed strips] as JPEG bytes, 'image/jpeg'). Falls back to the original on any error."""
    try:
        img = Image.open(io.BytesIO(content))
        img = ImageOps.exif_transpose(img).convert("RGB")
    except (UnidentifiedImageError, OSError, ValueError):
        logger.warning("Could not pre-process image; sending it unchanged")
        return [content], ""
    # Lift faint ballpoint ink off grey/coloured paper without changing the shapes of letters.
    img = ImageOps.autocontrast(img, cutoff=1)
    images = [_fit(img)] + [_fit(strip) for strip in _strips(img)]
    return [_encode(i) for i in images], "image/jpeg"
