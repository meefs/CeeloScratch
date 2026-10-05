"""Assemble turntable frames into a looping GIF and record it in the asset's asset.json.

    python tools/make_gif.py --frames logs/turntable_frames \
        --asset-dir assets/props/food/pink_donut_sprinkles/v001
"""

import argparse
import json
from pathlib import Path

from PIL import Image


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--frames", required=True, help="folder of frame_NNN.png files")
    parser.add_argument("--asset-dir", required=True, help="versioned asset folder containing asset.json")
    args = parser.parse_args()

    asset_dir = Path(args.asset_dir)
    meta_path = asset_dir / "asset.json"
    meta = json.loads(meta_path.read_text())
    fps = meta.get("turntable", {}).get("fps", 16)

    paths = sorted(Path(args.frames).glob("frame_*.png"))
    if not paths:
        raise SystemExit(f"no frames in {args.frames}")
    # One shared adaptive palette (from the first frame) keeps colours stable; no dithering halves
    # the file size at the cost of slight banding in the backdrop.
    first = Image.open(paths[0]).convert("RGB")
    palette = first.quantize(colors=255, method=Image.Quantize.MEDIANCUT)
    frames = [Image.open(p).convert("RGB").quantize(palette=palette, dither=Image.Dither.NONE)
              for p in paths]

    stem = f"{meta['asset']}_{meta['version']}"
    rel = f"renders/{stem}_turntable.gif"
    out = asset_dir / rel
    out.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(out, save_all=True, append_images=frames[1:], duration=round(1000 / fps),
                   loop=0, optimize=True, disposal=1)

    meta["files"]["turntable_gif"] = rel
    meta_path.write_text(json.dumps(meta, indent=2) + "\n")
    print(f"{out}: {len(frames)} frames @ {fps} fps, {out.stat().st_size / 1e6:.2f} MB")


if __name__ == "__main__":
    main()
