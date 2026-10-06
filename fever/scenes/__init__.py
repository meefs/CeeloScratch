"""Scene registry: every module in this folder (not starting with "_") is a Fever Dream scene.

A scene module defines:
    SCENE = {...}               a pure literal (read without Blender by fever/tools/*.py)
    build(ctx) -> state          build the static scene once per shard
    frame(ctx, state, t, f)      pose everything for loop time t in [0, 1); must not depend on earlier frames
"""

import importlib
from pathlib import Path

SCENE_DIR = Path(__file__).parent


def scene_ids():
    return sorted(p.stem for p in SCENE_DIR.glob("*.py") if not p.stem.startswith("_"))


def load_scene(scene_id):
    if scene_id not in scene_ids():
        raise SystemExit(f"unknown scene '{scene_id}'; available: {', '.join(scene_ids())}")
    return importlib.import_module(f"fever.scenes.{scene_id}")
