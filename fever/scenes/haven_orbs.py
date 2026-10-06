"""A slow vortex of orbs, each one a window into a different Poly Haven world.

Every orb shades with another downloaded HDRI looked up along its reflection vector, so it reads as a
glass marble holding a whole environment, which also spins inside it. Orbs ride torus-knot orbits with
whole-number lap counts per loop; a chrome planet at the centre reflects the whole swarm.
"""

import math

import numpy as np

from fever.core import geo, looks, props
from fever.core.assets import World

SCENE = {
    "id": "haven_orbs",
    "title": "Every World at Once",
    "logline": "A vortex of marbles, each holding a different Poly Haven world spinning inside it, orbiting a "
               "chrome planet that reflects them all.",
    "seconds": 16,
    "fps": 24,
    "shards": 8,
    "haven": {"hdris": {"world": ["night", "studio", "dark"]}, "hdri_pool": 24},
}

TAU = 2 * math.pi


def build(ctx):
    world = World(ctx, strength=0.2, fallback=((0.0, 0.0, 0.0), (0.03, 0.01, 0.06)))
    pool = ctx.hdri_pool()
    if not pool:
        raise SystemExit("haven_orbs needs a pool of Poly Haven HDRIs (selection 'hdri_pool')")
    portals = [looks.hdri_portal(f"MAT_world_{i:02d}", p) for i, p in enumerate(pool)]
    coll = geo.new_collection("ORBS")
    rng = ctx.rng(11)
    orbs = []
    for i in range(ctx.count(160, 40)):
        mat, mapping = portals[i % len(portals)]
        r = rng.uniform(0.12, 0.42)
        orb = props.sphere(f"orb_{i}", r, mat, coll, segments=32)
        orbs.append({"obj": orb, "mapping": mapping, "p": rng.choice((1, 2, 3)), "q": rng.choice((2, 3, 5)),
                     "R": rng.uniform(2.2, 4.2), "r": rng.uniform(0.4, 1.4), "phase": rng.random(),
                     "laps": rng.choice((1, 1, 2)), "tilt": rng.uniform(-0.6, 0.6)})
    planet = props.sphere("planet", 1.1, looks.principled("MAT_chrome", (0.95, 0.95, 0.97), 0.03, 1.0), coll, 64)
    rim = looks.iridescent("MAT_rings", roughness=0.2, glow=0.6)
    ring = geo.mesh_object("ring", *_ring(1.6, 2.1, 128), coll, smooth=True)
    ring.data.materials.append(rim)
    print(f"[fever] haven orbs: {len(orbs)} orbs over {len(pool)} Poly Haven worlds")
    return {"world": world, "orbs": orbs, "portals": portals, "ring": ring, "planet": planet}


def _ring(r0, r1, n):
    a = np.linspace(0, TAU, n, endpoint=False)
    verts = np.concatenate([np.stack([r0 * np.cos(a), r0 * np.sin(a), np.zeros(n)], 1),
                            np.stack([r1 * np.cos(a), r1 * np.sin(a), np.zeros(n)], 1)])
    faces = [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
    return verts, faces


def frame(ctx, st, t, f):
    st["world"].set(hue_shift=t)
    for i, (_, mapping) in enumerate(st["portals"]):
        mapping.inputs["Rotation"].default_value[2] = TAU * (t if i % 2 else -t)
    for o in st["orbs"]:
        u = TAU * (o["phase"] + o["laps"] * t)
        p = geo.torus_knot(o["p"], o["q"], o["R"], o["r"], np.array(u))
        c, s = math.cos(o["tilt"]), math.sin(o["tilt"])
        p = np.array([p[0], c * p[1] - s * p[2], s * p[1] + c * p[2]])
        o["obj"].location = p
    st["ring"].rotation_euler = (0.35 + 0.1 * math.sin(TAU * t), 0.2, TAU * t)
    a = TAU * t
    eye = np.array([7.5 * math.cos(a), 7.5 * math.sin(a), 2.2 * math.sin(2 * a) + 1.0])
    geo.set_camera(eye, np.zeros(3), lens=32)
