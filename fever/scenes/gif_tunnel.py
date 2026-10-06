"""A GIF taken apart into translucent frames, strung along a closed trefoil-knot track; the camera flies
through them at the GIF's own frame rate, so the animation re-forms as you rush through it.

Panes sit at even arc-length spacing along a (2,3) torus knot, oriented with the track, each slowly
corkscrewed. Every pane is drawn three times (red, green, blue) with slight offsets, so motion leaves
chromatic trails. Pane count is a whole multiple of the GIF's frame count, so the loop closes exactly.
Default GIF: Eadweard Muybridge's 1878 galloping horse (public domain), set in fever/tools/decompose_gif.py.
"""

import json
import math

import numpy as np

from fever.core import geo, looks
from fever.core.assets import World

SCENE = {
    "id": "gif_tunnel",
    "title": "Flipbook Wormhole",
    "logline": "A GIF decomposed into translucent panes along a trefoil knot; the camera flies through them "
               "at the GIF's frame rate and the animation re-assembles around you.",
    "seconds": 16,
    "fps": 24,
    "shards": 8,
    "render": {"transparent_bounces": 128},
    "haven": {"hdris": {"world": ["night", "studio", "dark"]}},
}

TAU = 2 * math.pi
KNOT = (2, 3, 7.0, 2.6)
PANE_HEIGHT = 1.7


def build(ctx):
    world = World(ctx, strength=0.12, fallback=((0.0, 0.0, 0.0), (0.04, 0.0, 0.08)))
    gif = ctx.gif_dir()
    if gif is None:
        raise SystemExit("gif_tunnel needs decomposed GIF frames in <assets>/gif (fever/tools/decompose_gif.py)")
    meta = json.loads((gif / "meta.json").read_text())
    n_img = len(meta["frames"])
    delay = float(np.clip(np.mean(meta["durations"]), 0.04, 0.2))
    reps = max(1, round(SCENE["seconds"] / delay / n_img))
    panes = reps * n_img
    ctx.used["gif"] = {"source": meta.get("source"), "frames": n_img, "panes": panes}

    dense = geo.torus_knot(*KNOT, np.linspace(0, TAU, 6000, endpoint=False))
    path, length = geo.resample_closed(dense, panes * 8)
    tangent, normal, binormal = geo.frames_closed(path)

    mats = []
    for i, name in enumerate(meta["frames"]):
        mat, hue = looks.glowing_image(f"MAT_gif_{i:03d}", gif / name, strength=1.5)
        mats.append((mat, hue))
    aspect = meta["width"] / meta["height"]
    hw, hh = PANE_HEIGHT * aspect / 2, PANE_HEIGHT / 2
    quad = [(-hw, -hh, 0), (hw, -hh, 0), (hw, hh, 0), (-hw, hh, 0)]
    coll = geo.new_collection("PANES")
    sources = []
    for i, (mat, _) in enumerate(mats):
        src = geo.mesh_object(f"pane_src_{i}", quad, [(0, 1, 2, 3)], coll, smooth=False,
                              uvs=[(0, 0), (1, 0), (1, 1), (0, 1)])
        src.data.materials.append(mat)
        src.hide_render = True
        sources.append(src)

    channels = [(1.0, 0.15, 0.25), (0.15, 1.0, 0.3), (0.25, 0.3, 1.0)]
    items = []
    for j in range(panes):
        k = j * 8
        roll = TAU * 3 * j / panes  # three full corkscrew turns around the knot
        n_vec = math.cos(roll) * normal[k] + math.sin(roll) * binormal[k]
        x_axis = np.cross(n_vec, tangent[k])
        for c, rgb in enumerate(channels):
            obj = geo.link_copy(sources[j % n_img], coll, f"pane_{j}_{c}")
            offset = tangent[k] * (c - 1) * 0.07 + x_axis * (c - 1) * 0.025
            obj.matrix_world = geo.basis(x_axis, n_vec, tangent[k], path[k] + offset)
            items.append((obj, j / panes, rgb))
    print(f"[fever] gif tunnel: {n_img} GIF frames x {reps} = {panes} panes along {length:.1f} m of knot")
    return {"world": world, "path": path, "tangent": tangent, "normal": normal, "binormal": binormal,
            "length": length, "items": items, "hues": [h for _, h in mats], "panes": panes}


def frame(ctx, st, t, f):
    st["world"].set(hue_shift=-t, saturation=1.4)
    for hue in st["hues"]:
        hue.inputs["Hue"].default_value = (0.5 + 0.5 * math.sin(TAU * t)) % 1.0
    for obj, u, rgb in st["items"]:
        d = ((u - t) % 1.0) * st["length"]  # distance ahead of the camera along the track
        fade = np.clip(d / 0.8, 0, 1) * (1 - np.clip((d - 5.0) / 6.0, 0, 1))
        obj.color = (*rgb, 0.7 * float(fade))
    eye = geo.along_closed(st["path"], t - 0.003)
    ahead = geo.along_closed(st["path"], t + 0.006)
    roll = TAU * 3 * t  # follow the panes' corkscrew so they stay upright as we fly
    up = math.cos(roll) * geo.along_closed(st["normal"], t) + math.sin(roll) * geo.along_closed(st["binormal"], t)
    geo.camera_basis(eye, ahead - eye, up, lens=20)
