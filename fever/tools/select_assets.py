"""Pick each scene's Poly Haven assets from the downloaded pool, by the keyword wishes in its SCENE["haven"].

Writes <out>/selection.json and copies only the chosen asset folders into <out>, so render jobs download
a small artifact instead of the whole pool. Choices are deterministic (stable across shards and reruns).

    python fever/tools/select_assets.py --haven ~/haven --out haven_selected
"""

import argparse
import json
import shutil
import zlib
from pathlib import Path

from plan import load_specs


def catalog(haven):
    """id -> main file (relative to haven) for each asset type that is actually usable."""
    def ids(kind, pattern):
        out = {}
        for d in sorted((haven / kind).glob("*")) if (haven / kind).exists() else []:
            hit = sorted(d.glob(pattern))
            if hit:
                out[d.name] = hit[0].relative_to(haven).as_posix()
        return out
    return {
        "hdris": ids("hdris", "*.hdr"),
        "textures": {k: f"textures/{k}" for k, v in ids("textures", "*diff*").items()},
        "models": ids("models", "*.blend"),
    }


def choose(scene_id, role, keywords, pool):
    for kw in keywords:
        matches = sorted(k for k in pool if kw.lower() in k.lower())
        if matches:
            return pool[matches[zlib.crc32(f"{scene_id}/{role}".encode()) % len(matches)]]
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--haven", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    haven, out = Path(args.haven).expanduser(), Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    cat = catalog(haven)
    print({k: len(v) for k, v in cat.items()})
    selection, chosen = {"_catalog": {k: sorted(v) for k, v in cat.items()}}, set()
    for sid, spec in load_specs().items():
        wishes = spec.get("haven", {})
        sel = {"hdris": {}, "textures": {}, "models": {}}
        for kind in ("hdris", "textures", "models"):
            for role, keywords in wishes.get(kind, {}).items():
                pick = choose(sid, role, keywords, cat[kind])
                if pick is None and kind == "hdris" and cat["hdris"]:
                    pick = cat["hdris"][sorted(cat["hdris"])[zlib.crc32(sid.encode()) % len(cat["hdris"])]]
                if pick:
                    sel[kind][role] = pick
                    chosen.add(pick)
        n_pool = wishes.get("hdri_pool", 0)
        if n_pool and cat["hdris"]:
            names = sorted(cat["hdris"])
            step = max(1, len(names) // n_pool)
            sel["hdri_pool"] = [cat["hdris"][n] for n in names[::step][:n_pool]]
            chosen.update(sel["hdri_pool"])
        selection[sid] = sel
        print(f"{sid}: {json.dumps(sel)}")
    for rel in sorted(chosen):
        src = haven / rel
        folder = src if src.is_dir() else src.parent
        dest = out / folder.relative_to(haven)
        if not dest.exists():
            shutil.copytree(folder, dest)
    (out / "selection.json").write_text(json.dumps(selection, indent=2))
    size = sum(f.stat().st_size for f in out.rglob("*") if f.is_file())
    print(f"selected {len(chosen)} assets, {size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
