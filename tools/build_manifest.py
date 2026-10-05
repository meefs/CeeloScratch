"""Write manifest.json: the map of this repository's filesystem.

It records the agreed folder layout (what each top-level area is for) and every
file in the repo with its size, SHA-256 and role, so later pipelines can find
and verify assets without guessing. Run from the repository root:

    python tools/build_manifest.py
"""

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "manifest.json"

LAYOUT = {
    ".github/workflows/": "GitHub Actions pipelines (runner jobs).",
    "assets/": "Generated deliverables. Pattern: assets/<category>/<subcategory>/<asset_name>/<version>/",
    "assets/<...>/<version>/<asset>_<version>.blend": "Editable Blender source scene (asset + stage).",
    "assets/<...>/<version>/<asset>_<version>.glb": "Real-time glTF binary of the asset only (Y-up, meters).",
    "assets/<...>/<version>/renders/": "Rendered stills and turntable GIF of that version.",
    "assets/<...>/<version>/asset.json": "Metadata: parts, poly counts, render settings, tool versions.",
    "assets/<...>/<version>/mcp_transcript.json": "Every MCP tool call that built the version, with replies.",
    "blender/mcp/": "Glue for driving Blender through MCP for Blender (headless host, server launcher, client).",
    "blender/recipes/<asset_name>/": "Ordered steps (NN_name.py), each sent to Blender as one execute_blender_code call.",
    "tools/": "Repository housekeeping scripts (manifest, README).",
}

ROLES = [
    ("assets/", ".blend", "blender-source"),
    ("assets/", ".glb", "gltf-binary"),
    ("assets/", ".png", "render"),
    ("assets/", ".gif", "turntable"),
    ("assets/", "asset.json", "asset-metadata"),
    ("assets/", "mcp_transcript.json", "build-transcript"),
    (".github/workflows/", "", "workflow"),
    ("blender/recipes/", ".py", "recipe-step"),
    ("blender/mcp/", ".py", "mcp-glue"),
    ("tools/", ".py", "tooling"),
]


def role_of(path):
    for prefix, suffix, role in ROLES:
        if path.startswith(prefix) and path.endswith(suffix):
            return role
    return "repo-meta"


def tracked_files():
    out = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
                         cwd=ROOT, check=True, capture_output=True).stdout.decode()
    return sorted({p for p in out.split("\0") if p and p != MANIFEST.name and (ROOT / p).is_file()})


def main():
    files = []
    for rel in tracked_files():
        data = (ROOT / rel).read_bytes()
        files.append({"path": rel, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
                      "role": role_of(rel)})
    assets = []
    for meta_path in sorted(ROOT.glob("assets/**/asset.json")):
        meta = json.loads(meta_path.read_text())
        folder = meta_path.parent.relative_to(ROOT).as_posix()
        assets.append({"asset": meta.get("asset"), "version": meta.get("version"), "path": folder + "/",
                       "files": {k: f"{folder}/{v}" for k, v in meta.get("files", {}).items()}})
    manifest = {
        "schema": "ceeloscratch.manifest/1",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "layout": LAYOUT,
        "assets": assets,
        "files": files,
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"manifest.json: {len(files)} files, {len(assets)} asset versions")


if __name__ == "__main__":
    main()
