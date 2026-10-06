"""Give every MP4 under assets/ an autoplaying README preview (<stem>_preview.webp), if it lacks one.

MP4s already described by an asset.json / scene.json (which name their own preview) are skipped.

    python tools/make_previews.py
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENCODER = ROOT / "tools" / "looks" / "encode_webp.py"


def covered():
    """MP4 paths already given a preview by a pipeline's metadata."""
    done = set()
    for meta in list(ROOT.glob("assets/**/asset.json")) + list(ROOT.glob("assets/**/scene.json")):
        files = json.loads(meta.read_text()).get("files", {})
        if any(str(v).endswith(".webp") for v in files.values()):
            done |= {(meta.parent / v).resolve() for v in files.values() if str(v).endswith(".mp4")}
    return done


def main():
    skip = covered()
    made = 0
    for mp4 in sorted(ROOT.glob("assets/**/*.mp4")):
        preview = mp4.with_name(f"{mp4.stem}_preview.webp")
        if mp4.resolve() in skip or preview.exists() or mp4.with_suffix(".webp").exists():
            continue
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(mp4), "-vf", "fps=12,scale=480:-2:flags=area",
                            f"{tmp}/frame_%05d.png"], check=True)
            subprocess.run([sys.executable, str(ENCODER), tmp, str(preview), "--fps", "12", "--quality", "55"],
                           check=True)
        made += 1
        print(f"preview: {preview.relative_to(ROOT)}")
    print(f"{made} new previews")


if __name__ == "__main__":
    main()
