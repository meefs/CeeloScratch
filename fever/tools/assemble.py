"""Turn a scene's rendered frames into its deliverables.

standard/high quality: <id>.mp4 (full res, scene fps), <id>_preview.webp (480 px, half fps, for the README),
<id>_poster.png, scene.json. Preview quality: a contact sheet of the sampled frames plus scene.json.

    python fever/tools/assemble.py --scene hat_tower --frames frames --stats frames --out video/hat_tower \
        --quality standard
"""

import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path

from PIL import Image

from plan import load_specs


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--scene", required=True)
    parser.add_argument("--frames", required=True)
    parser.add_argument("--stats", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--quality", default="standard")
    args = parser.parse_args()
    spec = load_specs()[args.scene]
    frames = sorted(Path(args.frames).glob("frame_*.png"))
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    stats = [json.loads(p.read_text()) for p in sorted(Path(args.stats).glob(f"stats_{args.scene}_*.json"))]
    seconds = [s for st in stats for s in st["frame_seconds"].values()]
    meta = {k: spec[k] for k in ("id", "title", "logline", "seconds", "fps")}
    meta.update({
        "quality": args.quality, "frames_rendered": len(frames), "frames_per_loop": spec["frames"],
        "resolution": stats[0]["resolution"] if stats else None, "samples": stats[0]["samples"] if stats else None,
        "blender": stats[0].get("blender") if stats else None, "shards": len(stats),
        "render_seconds_total": round(sum(seconds), 1),
        "render_seconds_per_frame": round(sum(seconds) / max(len(seconds), 1), 2),
        "haven_assets": stats[0]["haven_assets"] if stats else {},
        "workflow_run": (f"{os.environ['GITHUB_SERVER_URL']}/{os.environ['GITHUB_REPOSITORY']}/actions/runs/"
                         f"{os.environ['GITHUB_RUN_ID']}" if os.environ.get("GITHUB_RUN_ID") else None),
    })
    sid = args.scene
    if args.quality == "preview":
        thumbs = [Image.open(p).convert("RGB") for p in frames]
        w, h = thumbs[0].size
        cols = 3
        sheet = Image.new("RGB", (w * cols, h * ((len(thumbs) + cols - 1) // cols)))
        for i, im in enumerate(thumbs):
            sheet.paste(im, ((i % cols) * w, (i // cols) * h))
        sheet.save(out / f"{sid}_contact.png")
        meta["files"] = {"contact": f"{sid}_contact.png"}
    else:
        if len(frames) != spec["frames"]:
            raise SystemExit(f"{sid}: expected {spec['frames']} frames, got {len(frames)}")
        work = out / "_seq"
        work.mkdir(exist_ok=True)
        for i, p in enumerate(frames):  # contiguous numbering for ffmpeg
            dst = work / f"f_{i:05d}.png"
            if not dst.exists():
                os.link(p, dst)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(spec["fps"]), "-i",
                        str(work / "f_%05d.png"), "-c:v", "libx264", "-crf", "18", "-preset", "slow",
                        "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out / f"{sid}.mp4")], check=True)
        shutil.rmtree(work)
        half = frames[::2]

        def small(p):
            im = Image.open(p).convert("RGB")
            return im.resize((480, round(im.height * 480 / im.width)), Image.BOX)

        first = small(half[0])
        first.save(out / f"{sid}_preview.webp", save_all=True, append_images=(small(p) for p in half[1:]),
                   duration=round(2000 / spec["fps"]), loop=0, quality=55, method=4)
        Image.open(frames[len(frames) // 2]).save(out / f"{sid}_poster.png")
        meta["files"] = {"mp4": f"{sid}.mp4", "preview_webp": f"{sid}_preview.webp", "poster": f"{sid}_poster.png"}
    meta["sizes_mb"] = {k: round((out / v).stat().st_size / 1e6, 2) for k, v in meta["files"].items()}
    (out / "scene.json").write_text(json.dumps(meta, indent=2) + "\n")
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
