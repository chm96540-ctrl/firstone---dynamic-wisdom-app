"""Turn a clean reference scan into a realistic "phone photo" of the card.

Used two ways:
  * evaluation - measure how often the matcher finds the right card under realistic damage;
  * training   - later, to fine-tune the embedder (metric learning) without hand-labelled photos.

The images simulate what the matcher sees *after* the app has found and straightened the
card: a little leftover tilt/crop error, blur, glare, colour cast, sleeve sheen, JPEG noise.
"""

from __future__ import annotations

import io
import random

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter


def _perspective_jitter(img: Image.Image, rng: random.Random, strength: float) -> Image.Image:
    w, h = img.size
    d = strength * min(w, h)

    def j() -> float:
        return rng.uniform(-d, d)

    # Source quad corners (TL, BL, BR, TR) for Image.QUAD.
    quad = (j(), j(), j(), h + j(), w + j(), h + j(), w + j(), j())
    return img.transform((w, h), Image.Transform.QUAD, quad, Image.Resampling.BILINEAR)


def _glare(img: Image.Image, rng: random.Random) -> Image.Image:
    w, h = img.size
    overlay = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(overlay)
    cx, cy = rng.uniform(0, w), rng.uniform(0, h)
    rx, ry = rng.uniform(0.1, 0.35) * w, rng.uniform(0.05, 0.2) * h
    draw.ellipse((cx - rx, cy - ry, cx + rx, cy + ry), fill=int(rng.uniform(90, 200)))
    overlay = overlay.filter(ImageFilter.GaussianBlur(radius=max(w, h) * 0.06))
    white = Image.new("RGB", (w, h), (255, 255, 255))
    return Image.composite(white, img, overlay)


def _sleeve_sheen(img: Image.Image, rng: random.Random) -> Image.Image:
    arr = np.asarray(img, dtype=np.float32)
    h, w = arr.shape[:2]
    angle = rng.uniform(0, np.pi)
    yy, xx = np.mgrid[0:h, 0:w]
    band = np.cos((xx * np.cos(angle) + yy * np.sin(angle)) / (0.15 * max(h, w)))
    arr += (band[..., None] * rng.uniform(5, 20)).astype(np.float32)
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


def _jpeg(img: Image.Image, rng: random.Random) -> Image.Image:
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=rng.randint(35, 85))
    buf.seek(0)
    return Image.open(buf).convert("RGB")


def phone_photo(img: Image.Image, rng: random.Random | None = None, severity: float = 1.0) -> Image.Image:
    """Return a randomly degraded copy of `img`. `severity` 0 = untouched, 1 = typical, 2 = harsh."""
    rng = rng or random.Random()
    out = img.convert("RGB")
    if severity <= 0:
        return out

    out = _perspective_jitter(out, rng, 0.03 * severity)
    out = out.rotate(rng.uniform(-3, 3) * severity, resample=Image.Resampling.BILINEAR, fillcolor=(30, 30, 30))
    out = ImageEnhance.Brightness(out).enhance(rng.uniform(1 - 0.3 * severity, 1 + 0.25 * severity))
    out = ImageEnhance.Contrast(out).enhance(rng.uniform(1 - 0.25 * severity, 1 + 0.2 * severity))
    out = ImageEnhance.Color(out).enhance(rng.uniform(1 - 0.3 * severity, 1 + 0.2 * severity))

    # Colour cast (warm indoor light / cool daylight).
    cast = np.array([rng.uniform(-12, 12) for _ in range(3)], dtype=np.float32) * severity
    out = Image.fromarray(np.clip(np.asarray(out, np.float32) + cast, 0, 255).astype(np.uint8))

    if rng.random() < 0.5 * severity:
        out = _glare(out, rng)
    if rng.random() < 0.3 * severity:
        out = _sleeve_sheen(out, rng)
    if rng.random() < 0.6:
        out = out.filter(ImageFilter.GaussianBlur(radius=rng.uniform(0, 1.5) * severity))
    return _jpeg(out, rng)
