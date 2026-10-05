"""Encode a folder of PNG frames as a looping animated WebP (libwebp via Pillow, no ffmpeg needed).

    python tools/looks/encode_webp.py <frames_dir> <out.webp> --fps 48 --quality 60 [--width 640]
"""

import argparse
from pathlib import Path

from PIL import Image


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("frames")
    parser.add_argument("out")
    parser.add_argument("--fps", type=float, default=48)
    parser.add_argument("--quality", type=int, default=75)
    parser.add_argument("--width", type=int, help="downscale to this width (area filter)")
    args = parser.parse_args()

    paths = sorted(Path(args.frames).glob("frame_*.png"))
    if not paths:
        raise SystemExit(f"no frames in {args.frames}")

    def load(p):
        img = Image.open(p).convert("RGB")
        if args.width and img.width != args.width:
            img = img.resize((args.width, round(img.height * args.width / img.width)), Image.BOX)
        return img

    first = load(paths[0])
    first.save(args.out, save_all=True, append_images=(load(p) for p in paths[1:]),
               duration=round(1000 / args.fps), loop=0, quality=args.quality, method=6, lossless=False)
    print(f"{args.out}: {len(paths)} frames, {Path(args.out).stat().st_size / 1e6:.2f} MB")


if __name__ == "__main__":
    main()
