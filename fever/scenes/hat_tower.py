"""A classical bust wearing cowboy hats stacked all the way to the ceiling, between two infinite mirrors.

The stack sways like a noodle (amplitude grows with height), each hat spins a little on its own phase,
and the colours roll up the tower. Two facing mirror walls repeat the whole thing forever while disco
spots circle and the camera cranes from floor to ceiling and back once per loop.
"""

import math

import bpy
import numpy as np

from fever.core import assets, geo, looks, props
from fever.core.assets import World

SCENE = {
    "id": "hat_tower",
    "title": "Hats to the Ceiling",
    "logline": "A marble bust wearing cowboy hats stacked to the ceiling, swaying between two mirrors that "
               "repeat it forever.",
    "seconds": 16,
    "fps": 24,
    "shards": 10,
    "render": {"glossy_bounces": 10},
    "haven": {
        "hdris": {"world": ["studio", "hall", "interior", "room", "loft"]},
        "textures": {"floor": ["parquet", "wood_floor", "herringbone", "floor", "carpet"],
                     "wall": ["wallpaper", "plaster", "painted", "fabric"],
                     "pedestal": ["marble"]},
        "models": {"man": ["bust", "statue", "sculpture", "head"]},
    },
}

TAU = 2 * math.pi
ROOM = 8.0
CEILING = 7.2
PEDESTAL = 1.05
BUST = 0.78
PITCH = 0.105  # each hat nests into the crown below


def _box(name, size, location, material, collection):
    sx, sy, sz = size
    v = [(x * sx / 2, y * sy / 2, z * sz) for z in (0, 1) for y in (-1, 1) for x in (-1, 1)]
    faces = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    uvs = [(p[0] + p[2], p[1] + p[2]) for p in v]
    obj = geo.mesh_object(name, v, faces, collection, smooth=False, uvs=uvs)
    obj.location = location
    obj.data.materials.append(material)
    return obj


def build(ctx):
    world = World(ctx, strength=0.6)
    room = geo.new_collection("ROOM")
    floor = geo.grid_plane("floor", ROOM, ROOM, 2.0, room)
    floor.data.materials.append(assets.texture_material(ctx, "floor", (0.4, 0.25, 0.15)))
    ceiling = geo.grid_plane("ceiling", ROOM, ROOM, 2.0, room)
    ceiling.location.z = CEILING
    ceiling.rotation_euler.x = math.pi
    ceiling.data.materials.append(looks.principled("MAT_ceiling", (0.85, 0.82, 0.78), 0.9))
    wall_mat = assets.texture_material(ctx, "wall", (0.5, 0.2, 0.4))
    for sgn in (-1, 1):  # papered walls front and back
        wall = geo.grid_plane(f"wall_{sgn}", ROOM, CEILING, 1.5, room)
        wall.rotation_euler.x = math.pi / 2
        wall.location = (0, sgn * ROOM / 2, CEILING / 2)
        wall.data.materials.append(wall_mat)
    mirror_mat = looks.principled("MAT_mirror", (0.92, 0.92, 0.95), 0.015, 1.0)
    for sgn in (-1, 1):  # mirror walls left and right: infinite regress
        mirror = geo.grid_plane(f"mirror_{sgn}", ROOM, CEILING, 2.0, room)
        mirror.rotation_euler = (math.pi / 2, 0, math.pi / 2)
        mirror.location = (sgn * ROOM / 2, 0, CEILING / 2)
        mirror.data.materials.append(mirror_mat)

    _box("pedestal", (0.5, 0.5, PEDESTAL), (0, 0, 0), assets.texture_material(ctx, "pedestal", (0.9, 0.9, 0.9), 0.3),
         room)
    man = assets.load_model(ctx, "man", BUST) or props.bust_fallback()
    man.location.z = PEDESTAL

    src = props.cowboy_hat()
    src.hide_render = True
    head_top = PEDESTAL + BUST - 0.1
    n_hats = int((CEILING - head_top) / PITCH)
    hats = [geo.link_copy(src, room) for _ in range(n_hats)]

    spots = []
    for i in range(3):
        light = bpy.data.lights.new(f"spot_{i}", "SPOT")
        light.energy = 900
        light.spot_size = math.radians(28)
        light.spot_blend = 0.4
        obj = bpy.data.objects.new(f"spot_{i}", light)
        bpy.context.scene.collection.objects.link(obj)
        spots.append(obj)
    key = bpy.data.lights.new("key", "AREA")
    key.energy, key.size = 350, 2.0
    key_obj = bpy.data.objects.new("key", key)
    key_obj.location = (1.5, -2.5, 3.5)
    key_obj.rotation_euler = (math.radians(55), 0, math.radians(30))
    bpy.context.scene.collection.objects.link(key_obj)
    print(f"[fever] hat tower: {n_hats} hats from z={head_top:.2f} to the ceiling at {CEILING}")
    return {"world": world, "hats": hats, "head_top": head_top, "spots": spots}


def frame(ctx, st, t, f):
    st["world"].set(hue_shift=0.12 * math.sin(TAU * t))
    hats = st["hats"]
    n = len(hats)
    k = np.arange(n, dtype=float)
    sway_x = 0.0011 * k ** 1.6 * np.sin(TAU * t + 0.12 * k)
    sway_y = 0.0008 * k ** 1.6 * np.cos(TAU * t + 0.09 * k + 1.0)
    z = st["head_top"] + k * PITCH
    tilt_x = np.gradient(sway_y) / PITCH
    tilt_y = np.gradient(sway_x) / PITCH
    for i, hat in enumerate(hats):
        yaw = 0.37 * i + 0.25 * math.sin(TAU * 2 * t + 0.2 * i)
        squash = 0.55 if i == n - 1 else 1.0
        rot = (geo.Matrix.Rotation(math.atan(tilt_y[i]), 4, "Y") @ geo.Matrix.Rotation(-math.atan(tilt_x[i]), 4, "X")
               @ geo.Matrix.Rotation(yaw, 4, "Z"))
        hat.matrix_world = (geo.Matrix.Translation((sway_x[i], sway_y[i], z[i])) @ rot
                            @ geo.Matrix.Diagonal((1.15, 1.15, 1.15 * squash, 1)))
        hat.color = looks.hsv(0.618 * i + t, 0.55, 0.95)
    for i, spot in enumerate(st["spots"]):
        a = TAU * (t + i / 3)
        spot.location = (2.6 * math.cos(a), 2.6 * math.sin(a), 0.6 + 2.0 * i)
        aim = np.array([0.0, 0.0, 2.0 + 1.6 * i]) - np.array(spot.location)
        spot.matrix_world = geo.look_at(np.array(spot.location), np.array(spot.location) + aim)
        spot.data.color = looks.hsv(t + i / 3, 0.85)[:3]
    climb = 0.5 - 0.5 * math.cos(TAU * t)
    zc = 1.5 + 5.0 * climb
    a = TAU * t
    eye = np.array([3.0 * math.cos(a), 3.0 * math.sin(a) * 0.8, zc])
    target = np.array([0.0, 0.0, min(max(zc + 0.35, 1.5), CEILING - 0.4)])
    geo.set_camera(eye, target, lens=22)
