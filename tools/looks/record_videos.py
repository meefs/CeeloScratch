"""Add the v002 videos and how they were made to the version's asset.json.

    python tools/looks/record_videos.py assets/props/food/pink_donut_sprinkles/v002 --frames 288 --shards 5
"""

import argparse
import json
import os
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("asset_dir")
    parser.add_argument("--frames", type=int, required=True)
    parser.add_argument("--shards", type=int, required=True)
    parser.add_argument("--render-run", help="run ID that rendered the frames, if not the current run")
    args = parser.parse_args()

    asset_dir = Path(args.asset_dir)
    meta_path = asset_dir / "asset.json"
    meta = json.loads(meta_path.read_text())
    stem = f"{meta['asset']}_{meta['version']}"
    renders = {
        "luscious_mp4": f"renders/{stem}_luscious_48fps.mp4",
        "luscious_webp": f"renders/{stem}_luscious_48fps.webp",
        "luscious_poster": f"renders/{stem}_luscious_poster.png",
        "crt_mp4": f"renders/{stem}_crt_48fps.mp4",
        "crt_readme_webp": f"renders/{stem}_crt_readme.webp",
        "crt_poster": f"renders/{stem}_crt_poster.png",
    }
    missing = [p for p in renders.values() if not (asset_dir / p).exists()]
    if missing:
        raise SystemExit(f"missing renders: {missing}")
    meta["files"].update(renders)
    meta["files"]["mcp_transcripts"] = sorted(p.name for p in asset_dir.glob("mcp_transcript_shard*.json"))
    meta["description"] = ("Pink-iced donut with rainbow sprinkles, luscious look: wet glossy icing, glamour "
                           "lighting, shallow focus. Real-world scale (~9 cm), Z-up in .blend, Y-up in .glb.")
    meta["turntable"] = {
        "frames": args.frames, "fps": 48, "resolution": [720, 540], "samples": 32,
        "rendered_on": f"{args.shards} parallel macOS arm64 runners, {args.frames // args.shards}-ish frames each",
    }
    meta["videos"] = {
        "luscious": {"speed": "real time, 6 s per turn", "fps": 48, "post": "tools/looks/vanity.py"},
        "crt": {"speed": "half speed, 12 s per turn (motion-interpolated 2x)", "fps": 48,
                "post": "tools/looks/crt_sim.py",
                "effects": ["70s film grade", "lamp breathing", "composite video bandwidth", "240-line beam scan",
                            "sync jitter", "blooming (raster swell + defocus with brightness)", "barrel tube geometry",
                            "phosphor persistence", "faceplate halation", "slot mask", "hum bar", "RF snow",
                            "glass reflection and bezel"]},
    }
    server, repo, run_id = (os.environ.get(k) for k in ("GITHUB_SERVER_URL", "GITHUB_REPOSITORY", "GITHUB_RUN_ID"))
    if server and repo and run_id:
        meta["workflow_run"] = f"{server}/{repo}/actions/runs/{run_id}"
        if args.render_run and args.render_run != run_id:
            meta["render_run"] = f"{server}/{repo}/actions/runs/{args.render_run}"
    meta["sizes_mb"] = {k: round(os.path.getsize(asset_dir / v) / 1e6, 2) for k, v in renders.items()}
    meta_path.write_text(json.dumps(meta, indent=2) + "\n")
    print(json.dumps(meta["sizes_mb"]))


if __name__ == "__main__":
    main()
