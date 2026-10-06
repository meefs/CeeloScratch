"""Run context shared by every Fever Dream scene: loop timing, quality presets, chosen Poly Haven assets.

Every scene is a seamless loop. A frame's state is a pure function of loop time ``t`` in [0, 1),
so frames can be rendered in any order, on any runner, and frame N stitches cleanly onto frame 0.
Anything periodic must use whole-number frequencies of ``t`` (``sin(2*pi*k*t)`` with integer k).
"""

import json
import math
import random
from pathlib import Path

QUALITY = {
    # width in px (height follows the scene's aspect), Cycles samples, and a "detail" multiplier
    # that scenes apply to instance counts (chairs, butterflies, hairs) so previews stay quick.
    "preview": {"width": 480, "samples": 8, "detail": 0.25, "preview_frames": 6},
    "standard": {"width": 960, "samples": 24, "detail": 1.0},
    "high": {"width": 1280, "samples": 48, "detail": 1.0},
}
ASPECTS = {"16:9": 9 / 16, "4:3": 3 / 4, "1:1": 1.0}
TAU = 2 * math.pi


class Ctx:
    def __init__(self, spec, quality, assets_dir, seed=1970):
        self.spec = spec
        self.id = spec["id"]
        self.fps = spec.get("fps", 24)
        self.n_frames = int(round(spec["seconds"] * self.fps))
        q = QUALITY[quality]
        self.quality = quality
        self.width = q["width"]
        self.height = int(round(q["width"] * ASPECTS[spec.get("aspect", "16:9")] / 2)) * 2
        self.samples = q["samples"]
        self.detail = q["detail"]
        self.assets = Path(assets_dir).resolve()
        selection_file = self.assets / "selection.json"
        selection = json.loads(selection_file.read_text()) if selection_file.exists() else {}
        self.selection = selection.get(self.id, {})
        self.seed = seed
        self.used = {}  # Poly Haven assets actually used, recorded in the render stats

    # --- timing -------------------------------------------------------------------------------
    def t(self, frame):
        return frame / self.n_frames

    def count(self, n, minimum=1):
        """Scale an instance count by the quality's detail level."""
        return max(minimum, int(round(n * self.detail)))

    def rng(self, salt=0):
        return random.Random(self.seed * 7919 + salt)

    # --- Poly Haven assets chosen for this scene by fever/tools/select_assets.py ----------------
    def _path(self, rel, kind, role):
        if not rel:
            print(f"[fever] {self.id}: no Poly Haven {kind} for '{role}', using the procedural fallback")
            return None
        path = self.assets / rel
        if not path.exists():
            print(f"[fever] {self.id}: selected {kind} missing on disk: {path}")
            return None
        self.used.setdefault(kind, {})[role] = rel
        return path

    def hdri(self, role="world"):
        return self._path(self.selection.get("hdris", {}).get(role), "hdri", role)

    def hdri_pool(self):
        pool = [self.assets / rel for rel in self.selection.get("hdri_pool", []) if (self.assets / rel).exists()]
        self.used["hdri_pool"] = [str(p.relative_to(self.assets)) for p in pool]
        return pool

    def texture(self, role):
        return self._path(self.selection.get("textures", {}).get(role), "texture", role)

    def model(self, role):
        return self._path(self.selection.get("models", {}).get(role), "model", role)

    def gif_dir(self):
        d = self.assets / "gif"
        return d if (d / "meta.json").exists() else None
