import blenderproc as bproc  # BlenderProc must be imported first

"""Provision BlenderProc's Blender once (Blender itself, BlenderProc's packages, scikit-image) before caching it."""

import bpy

bproc.init()
from skimage import measure  # noqa: E402,F401  (installed with `blenderproc pip install scikit-image`)

print(f"[fever] warm-up OK: Blender {bpy.app.version_string}, scikit-image available")
