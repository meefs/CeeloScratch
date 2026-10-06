"""Take a GIF apart into RGBA frames for the Flipbook Wormhole scene.

The background (median border colour) is keyed down to a faint veil, so each frame becomes a translucent
pane with an opaque subject. Frames are composited (GIF disposal handled by Pillow), capped at 60 and
scaled to at most 512 px.

    python fever/tools/decompose_gif.py --url <gif url> --fallback <local gif> --out haven_selected/gif
"""

import argparse
import json
import urllib.request
from pathlib import Path

import numpy as np
from PIL import Image, ImageSequence

# Eadweard Muybridge, "The Horse in Motion" (1878), public domain, via Wikimedia Commons.
DEFAULT_URL = "https://upload.wikimedia.org/wikipedia/commons/d/dd/Muybridge_race_horse_animated.gif"
UA = "CeeloScratch/1.0 (https://github.com/meefs/CeeloScratch; fever dreams render pipeline)"


def fetch(url, dest):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        dest.write_bytes(r.read())


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--url", default="")
    parser.add_argument("--fallback", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    url = args.url or DEFAULT_URL
    src = out / "source.gif"
    try:
        fetch(url, src)
        source = url
    except Exception as exc:  # network or 404: use the repo's own GIF instead
        print(f"::warning::could not fetch {url} ({exc}); using {args.fallback}")
        src.write_bytes(Path(args.fallback).read_bytes())
        source = args.fallback

    im = Image.open(src)
    frames, durations = [], []
    for fr in ImageSequence.Iterator(im):
        frames.append(fr.convert("RGBA"))
        durations.append(max(fr.info.get("duration", 80), 20) / 1000)
    if len(frames) > 60:
        idx = np.linspace(0, len(frames) - 1, 60).round().astype(int)
        frames = [frames[i] for i in idx]
        durations = [sum(durations) / 60] * 60
    scale = min(1.0, 512 / max(frames[0].size))
    size = (round(frames[0].width * scale), round(frames[0].height * scale))
    names = []
    for i, fr in enumerate(frames):
        a = np.asarray(fr.resize(size, Image.LANCZOS), dtype=np.float32) / 255
        border = np.concatenate([a[0], a[-1], a[:, 0], a[:, -1]])[:, :3]
        bg = np.median(border, axis=0)
        dist = np.linalg.norm(a[..., :3] - bg, axis=-1)
        subject = np.clip((dist - 0.08) / 0.2, 0, 1)
        a[..., 3] = np.minimum(a[..., 3], 0.18 + 0.82 * subject)
        name = f"frame_{i:03d}.png"
        Image.fromarray((a * 255 + 0.5).astype(np.uint8), "RGBA").save(out / name)
        names.append(name)
    meta = {"source": source, "frames": names, "durations": durations, "width": size[0], "height": size[1]}
    (out / "meta.json").write_text(json.dumps(meta, indent=2))
    print(f"{len(names)} frames at {size[0]}x{size[1]}, mean delay {np.mean(durations):.3f}s from {source}")


if __name__ == "__main__":
    main()
