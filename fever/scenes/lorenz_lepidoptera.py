"""The Lorenz attractor ("the butterfly") drawn by ~1500 butterflies, each unique, each flapping at its own speed.

Butterflies sit along the integrated trajectory and drift back and forth along it; every one has its own
wing pattern (a per-object seed feeding one shared procedural wing shader), size, and a whole-number flap
frequency between 4 and 64 beats per loop, so every wing returns to its starting pose at the loop point.
"""

import math

import bpy
import numpy as np

from fever.core import geo, looks, props
from fever.core.assets import World

SCENE = {
    "id": "lorenz_lepidoptera",
    "title": "Lorenz Lepidoptera",
    "logline": "The Lorenz butterfly drawn by fifteen hundred butterflies, each with its own wings and its own "
               "wingbeat, drifting along the chaos.",
    "seconds": 20,
    "fps": 24,
    "shards": 12,
    "haven": {"hdris": {"world": ["night", "starry", "moonless", "dusk", "studio"]}},
}

TAU = 2 * math.pi
SAMPLES = 20000


def build(ctx):
    world = World(ctx, strength=0.25, fallback=((0.0, 0.0, 0.02), (0.05, 0.02, 0.12)))
    traj = (geo.lorenz(9000, dt=0.004) - np.array([0.0, 0.0, 25.0])) * 0.11
    seg = np.linalg.norm(np.diff(traj, axis=0), axis=1)
    s = np.concatenate([[0.0], np.cumsum(seg)])
    u = np.linspace(0.0, s[-1], SAMPLES)
    curve = np.stack([np.interp(u, s, traj[:, k]) for k in range(3)], 1)

    flock = geo.new_collection("FLOCK")
    parts_coll = geo.new_collection("BUTTERFLY_PARTS", linked=False)
    parts = props.butterfly_parts(parts_coll)
    n = ctx.count(1500, 150)
    rng = ctx.rng(5)
    birds = []
    for i in range(n):
        body = geo.link_copy(parts["body"], flock, f"bfly_{i}")
        wings = []
        seed = rng.random()
        for side in ("R", "L"):
            w = geo.link_copy(parts[side], flock, f"bfly_{i}_{side}")
            w.parent = body
            w["wing_seed"] = seed
            wings.append(w)
        birds.append({
            "body": body, "wings": wings,
            "u": (i + rng.random()) / n * (SAMPLES - 1),
            "drift": rng.uniform(30, 260), "drift_k": rng.choice((1, 1, 2)), "phase": rng.random(),
            "flap_k": rng.randint(4, 64), "flap_phase": rng.random(), "size": rng.uniform(0.7, 1.5),
            "wobble": rng.uniform(0.02, 0.07),
        })

    trail = bpy.data.curves.new("lorenz_trail", "CURVE")
    trail.dimensions = "3D"
    trail.bevel_depth = 0.004
    spline = trail.splines.new("POLY")
    pts = curve[::6]
    spline.points.add(len(pts) - 1)
    spline.points.foreach_set("co", np.hstack([pts, np.ones((len(pts), 1))]).ravel())
    trail.materials.append(looks.principled("MAT_trail", (0.3, 0.2, 0.6), 0.5, emission=(0.6, 0.4, 1.0),
                                            strength=0.8))
    trail_obj = bpy.data.objects.new("lorenz_trail", trail)
    bpy.context.scene.collection.objects.link(trail_obj)

    key = bpy.data.lights.new("key", "AREA")
    key.energy, key.size = 400, 4.0
    key_obj = bpy.data.objects.new("key", key)
    key_obj.matrix_world = geo.look_at(np.array([4.0, -5.0, 6.0]), np.zeros(3))
    bpy.context.scene.collection.objects.link(key_obj)
    print(f"[fever] lorenz: {n} butterflies along {s[-1]:.0f} m of trajectory")
    return {"world": world, "curve": curve, "birds": birds}


def _sample(curve, idx):
    idx = np.clip(idx, 1, len(curve) - 2)
    i0 = np.floor(idx).astype(int)
    frac = (idx - i0)[:, None]
    pos = curve[i0] * (1 - frac) + curve[i0 + 1] * frac
    tangent = curve[i0 + 1] - curve[i0 - 1]
    return pos, tangent


def frame(ctx, st, t, f):
    st["world"].set(hue_shift=0.5 * t, saturation=1.2)
    birds = st["birds"]
    idx = np.array([b["u"] + b["drift"] * math.sin(TAU * (b["drift_k"] * t + b["phase"])) for b in birds])
    pos, tangent = _sample(st["curve"], idx)
    for b, p, tan in zip(birds, pos, tangent):
        right, fwd, up = geo.orthonormal(tan)
        w = TAU * (b["drift_k"] * t + b["phase"])
        p = p + b["wobble"] * (math.cos(w) * right + math.sin(w) * up)
        b["body"].matrix_world = geo.basis(right, fwd, up, p, b["size"])
        beat = 0.5 + 0.5 * math.sin(TAU * (b["flap_k"] * t + b["flap_phase"]))
        angle = 0.15 + 1.05 * beat ** 1.4
        b["wings"][0].rotation_euler = (0.0, -angle, 0.0)
        b["wings"][1].rotation_euler = (0.0, angle, 0.0)
    a = TAU * t
    r = 6.8 + 3.4 * math.cos(a)
    eye = np.array([r * math.cos(a), r * math.sin(a), 0.8 + 1.4 * math.sin(2 * a)])
    geo.set_camera(eye, np.array([0.0, 0.0, -0.2]), lens=30)
