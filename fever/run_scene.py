import blenderproc as bproc  # BlenderProc must be imported before anything else

"""Render one shard of one Fever Dream scene, headless, through BlenderProc.

    blenderproc run fever/run_scene.py --scene lorenz_lepidoptera --shard 0 --shards 8 \
        --quality standard --assets haven_selected --out out

Writes out/frames/frame_NNNN.png for this shard's frames and out/stats_<scene>_<shard>.json.
"""

import argparse
import json
import sys
import time
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fever.core import render  # noqa: E402
from fever.core.loop import Ctx  # noqa: E402
from fever.scenes import load_scene  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description="Render one shard of a Fever Dream scene")
    parser.add_argument("--scene", required=True)
    parser.add_argument("--shard", type=int, default=0)
    parser.add_argument("--shards", type=int, default=1)
    parser.add_argument("--quality", default="standard", choices=["preview", "standard", "high"])
    parser.add_argument("--assets", default="haven_selected")
    parser.add_argument("--out", default="out")
    parser.add_argument("--seed", type=int, default=1970)
    args = parser.parse_args()

    started = time.time()
    module = load_scene(args.scene)
    bproc.init()
    ctx = Ctx(module.SCENE, args.quality, args.assets, args.seed)
    render.configure(ctx, **module.SCENE.get("render", {}))
    state = module.build(ctx)
    built = time.time()
    print(f"[fever] {ctx.id}: scene built in {built - started:.1f}s, {ctx.width}x{ctx.height}, "
          f"{ctx.samples} spp, {ctx.n_frames} frames per loop", flush=True)

    frames = render.frames_for(ctx, args.shard, args.shards)
    seconds = render.render_frames(ctx, lambda f: module.frame(ctx, state, ctx.t(f), f), frames,
                                   Path(args.out) / "frames")
    stats = {"scene": ctx.id, "shard": args.shard, "shards": args.shards, "quality": args.quality,
             "resolution": [ctx.width, ctx.height], "samples": ctx.samples, "frames": frames,
             "build_seconds": round(built - started, 1), "frame_seconds": seconds,
             "haven_assets": ctx.used, "blender": bpy.app.version_string}
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / f"stats_{ctx.id}_{args.shard:02d}.json").write_text(json.dumps(stats, indent=2, default=str))


main()
