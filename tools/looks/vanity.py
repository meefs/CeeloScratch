"""Vanity filter: soft-focus glow, highlight bloom, warm-pink grade, saturation lift, vignette."""
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter


def blur(arr, radius):
    img = Image.fromarray((np.clip(arr, 0, 1) * 255).astype(np.uint8))
    return np.asarray(img.filter(ImageFilter.GaussianBlur(radius)), dtype=np.float32) / 255


def vanity(img):
    a = np.asarray(img.convert("RGB"), dtype=np.float32) / 255
    h, w, _ = a.shape
    # 1. Orton soft focus: screen-blend a blurred copy for that dreamy, airbrushed glow.
    soft = blur(a, w / 160)
    a = a * 0.78 + np.maximum(a, soft) * 0.22
    # 2. Bloom: only glints much brighter than their surroundings bleed light (wet icing),
    #    so the bright backdrop itself never glows.
    glint = np.clip(a - blur(a, w / 50) - 0.05, 0, 1)
    a = a + blur(glint, w / 90) * 1.6 + blur(glint, w / 30) * 1.0
    # 3. Warm pink grade: blush the shadows, cream the highlights.
    a = a * np.array([1.03, 0.975, 0.985], dtype=np.float32) + np.array([0.025, 0.004, 0.018], dtype=np.float32) * (1 - a)
    # 4. Saturation lift around luminance.
    lum = (a @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32))[..., None]
    a = lum + (a - lum) * 1.2
    # 5. Soft vignette.
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    r2 = ((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2
    a = a * (1 - 0.17 * np.clip(r2 - 0.2, 0, None) ** 1.1)[..., None]
    return Image.fromarray((np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8))


if __name__ == "__main__":
    src, dst = Path(sys.argv[1]), Path(sys.argv[2])
    if src.is_file():
        vanity(Image.open(src)).save(dst)
    else:
        dst.mkdir(parents=True, exist_ok=True)
        for p in sorted(src.glob("frame_*.png")):
            vanity(Image.open(p)).save(dst / p.name)
