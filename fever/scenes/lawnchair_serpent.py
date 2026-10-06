"""A serpent built from a two-level fractal of lawn chairs, slithering on a Poly Haven lawn.

Each body station is a rosette of rosettes: k1 sub-rings around the spine, each a ring of k2 chairs
radiating outwards like scales. The rings counter-rotate along the body and a rainbow flows tailwards.
The ground scrolls like a treadmill by exactly two texture tiles per loop, so the loop is seamless.
"""

import math

import bpy
import numpy as np

from fever.core import assets, geo, looks, props
from fever.core.assets import World

SCENE = {
    "id": "lawnchair_serpent",
    "title": "Lawn-Chair Serpent",
    "logline": "A serpent whose scales are rosettes of rosettes of lawn chairs, slithering across a lawn "
               "under a sky that cycles through every hue.",
    "seconds": 16,
    "fps": 24,
    "shards": 10,
    "haven": {
        "hdris": {"world": ["park", "garden", "meadow", "field", "sunflower", "grass", "sky"]},
        "textures": {"ground": ["grass", "lawn", "meadow", "moss", "leaves", "forest_floor"]},
        "models": {"chair": ["monobloc", "plastic_chair", "garden_chair", "lawn_chair", "outdoor_chair",
                             "folding_chair", "chair"]},
    },
}

TAU = 2 * math.pi
LENGTH = 16.0
TILE = 4.0


def spine(s, t):
    """Centre line (x, y) of the body; s=0 head, s=1 tail. A travelling wave runs tailwards."""
    amp = 0.45 + 1.7 * s
    return np.stack([-s * LENGTH, amp * np.sin(TAU * (1.4 * s - t)), np.zeros_like(s)], -1)


def radius(s):
    head = 1.0 + 0.35 * np.exp(-((s - 0.03) / 0.03) ** 2) - 0.25 * np.exp(-((s - 0.09) / 0.025) ** 2)
    taper = np.clip((1.0 - s) / 0.45, 0.12, 1.0)
    return 0.55 * head * taper


def build(ctx):
    world = World(ctx, strength=1.1)
    sun = bpy.data.lights.new("sun", "SUN")
    sun.energy = 2.5
    sun.angle = math.radians(8)
    sun_obj = bpy.data.objects.new("sun", sun)
    sun_obj.rotation_euler = (math.radians(50), 0, math.radians(30))
    bpy.context.scene.collection.objects.link(sun_obj)

    ground = geo.grid_plane("lawn", 140, 140, TILE)
    ground.data.materials.append(assets.texture_material(ctx, "ground", (0.15, 0.4, 0.1), 0.9))

    body = geo.new_collection("SERPENT")
    src = assets.load_model(ctx, "chair", 0.85)
    if src:
        for slot in src.material_slots:
            looks.tint_with_object_color(slot.material)
    else:
        src = props.lawn_chair()
    src.hide_render = True

    stations = ctx.count(64, 12)
    k1, k2 = (6, 5) if ctx.detail >= 1 else (5, 3)
    s_vals = (np.arange(stations) + 0.5) / stations
    chairs = []
    for n, s in enumerate(s_vals):
        for j in range(k1):
            for i in range(k2):
                chairs.append((geo.link_copy(src, body), s, j, i))

    tongue = [geo.link_copy(src, body) for _ in range(7)]
    eye_mat = looks.principled("MAT_eye", (1.0, 0.9, 0.2), 0.2, emission=(1.0, 0.85, 0.1), strength=6.0)
    eyes = []
    for side in (-1, 1):
        eyes.append((props.sphere(f"eye_{side}", 0.14, eye_mat, body), side))
    print(f"[fever] serpent: {len(chairs)} chairs ({stations} stations x {k1} x {k2})")
    return {"world": world, "ground": ground, "chairs": chairs, "k1": k1, "k2": k2, "tongue": tongue,
            "eyes": eyes, "chair_height": 0.85}


def frame(ctx, st, t, f):
    st["world"].set(hue_shift=t, saturation=1.25)
    st["ground"].location.x = -2 * TILE * t  # treadmill: two whole tiles per loop
    k1, k2 = st["k1"], st["k2"]
    ds = 1e-3
    for obj, s, j, i in st["chairs"]:
        p = spine(np.array(s), t)
        tangent = spine(np.array(s + ds), t) - p
        side, fwd, up = geo.orthonormal(-tangent)  # forward points headwards
        r1 = float(radius(s))
        r2 = 0.42 * r1
        scale = 1.1 * r2 / st["chair_height"]
        p = p + np.array([0, 0, r1 + r2 + 0.15])
        psi = TAU * (3 * s + t)
        theta = TAU * j / k1 + psi
        phi = TAU * i / k2 - 2 * psi + theta
        centre = p + r1 * (math.cos(theta) * side + math.sin(theta) * up)
        pos = centre + r2 * (math.cos(phi) * side + math.sin(phi) * up)
        radial = pos - p
        x_axis = np.cross(fwd, radial)
        obj.matrix_world = geo.basis(x_axis, np.cross(radial, x_axis), radial, pos, scale)
        obj.color = looks.hsv(1.4 * s + 0.12 * j / k1 - t, 0.8, 1.0)
    # Head: glowing eyes and a forked tongue of tiny red chairs flicking four times per loop.
    head = spine(np.array(0.0), t) + np.array([0, 0, radius(0.0) * 1.42 + 0.15])
    tangent = head - (spine(np.array(0.01), t) + np.array([0, 0, radius(0.01) * 1.42 + 0.15]))
    side, fwd, up = geo.orthonormal(tangent)
    for eye, sgn in st["eyes"]:
        eye.location = head + 0.35 * fwd + sgn * 0.3 * side + 0.32 * up
    flick = 0.5 + 0.5 * math.sin(TAU * 4 * t)
    for n, obj in enumerate(st["tongue"]):
        fork = (n - 3) * 0.06 * flick if n >= 4 else 0.0
        pos = head + fwd * (0.75 + 0.16 * n * (0.3 + 0.7 * flick)) + side * fork - up * 0.1
        obj.matrix_world = geo.basis(side, up, fwd, pos, 0.12)
        obj.color = (1.0, 0.05, 0.1, 1.0)
    centre = np.array([-5.6, 0.0, 0.9])
    a = TAU * t + 0.6
    eye_pos = centre + np.array([9.5 * math.cos(a), 9.5 * math.sin(a), 3.4 + 0.8 * math.sin(TAU * 2 * t)])
    geo.set_camera(eye_pos, centre, lens=26)
