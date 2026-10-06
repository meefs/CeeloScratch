"""Read every scene's SCENE literal (no Blender needed) and plan the GitHub Actions job matrix.

    python fever/tools/plan.py --scenes all --quality standard >> "$GITHUB_OUTPUT"
    python fever/tools/plan.py --meta lorenz_lepidoptera
"""

import argparse
import ast
import json
from pathlib import Path

SCENES = Path(__file__).resolve().parent.parent / "scenes"


def load_specs():
    specs = {}
    for path in sorted(SCENES.glob("*.py")):
        if path.stem.startswith("_"):
            continue
        tree = ast.parse(path.read_text())
        for node in tree.body:
            if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == "SCENE" for t in node.targets):
                spec = ast.literal_eval(node.value)
                spec["frames"] = int(round(spec["seconds"] * spec.get("fps", 24)))
                specs[spec["id"]] = spec
    return specs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenes", default="all")
    parser.add_argument("--quality", default="standard")
    parser.add_argument("--meta", help="print one scene's spec as JSON and exit")
    args = parser.parse_args()
    specs = load_specs()
    if args.meta:
        print(json.dumps(specs[args.meta]))
        return
    wanted = list(specs) if args.scenes.strip() in ("", "all") else [s.strip() for s in args.scenes.split(",")]
    unknown = [s for s in wanted if s not in specs]
    if unknown:
        raise SystemExit(f"unknown scenes {unknown}; available: {', '.join(specs)}")
    jobs = []
    for sid in wanted:
        shards = 1 if args.quality == "preview" else specs[sid].get("shards", 8)
        jobs += [{"scene": sid, "shard": i, "shards": shards} for i in range(shards)]
    print(f"render_matrix={json.dumps({'include': jobs})}")
    print(f"scenes={json.dumps(wanted)}")
    print(f"job_count={len(jobs)}")


if __name__ == "__main__":
    main()
