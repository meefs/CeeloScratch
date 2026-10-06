"""An endless spiral zoom into a console TV whose screen shows the room, whose TV shows the room, ...

A homage to Nam June Paik's video feedback pieces, built as true geometric recursion instead of feedback.
Level k of the room is level 0 mapped by M^k, where M is a similarity (scale S_LEVEL, twist THETA about the
viewing axis) that sends the camera's view rectangle at the screen plane onto the TV's screen hole.
The camera follows M^t applied to its start pose, so after one loop it sits exactly one level deeper and
the frame matches frame 0. Per-level hues shift in step (hue = base + DELTA * (k - t)) so colours match too.

Everything is self-lit (emission shading of Poly Haven textures), so lighting is identical at every scale.
Every object is kept inside the camera's level-0 view frustum, so the scaled copies always fit within the
TV's flared screen cavity and never poke out of the cabinet.
"""

import math

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

from fever.core import assets, geo, looks, props

SCENE = {
    "id": "paik_zoom",
    "title": "Paik's Spiral",
    "logline": "An infinite spiral zoom into a 1970s console TV that is showing the room it is in, forever.",
    "seconds": 12,
    "fps": 24,
    "shards": 6,
    "aspect": "4:3",
    "haven": {
        "hdris": {"world": ["studio"]},
        "textures": {"wall": ["wallpaper", "fabric", "plaster", "painted"],
                     "floor": ["carpet", "rug", "fabric", "parquet", "floor"],
                     "tv": ["wood", "walnut", "veneer", "parquet", "plywood"]},
        "models": {"chair": ["monobloc", "plastic_chair", "garden_chair", "lawn_chair", "armchair", "chair"]},
    },
}

TAU = 2 * math.pi
S_LEVEL = 0.3            # scale from one level to the next
THETA = math.radians(24)  # twist per level about the viewing axis
LEVELS = 8               # 0.3^7 of the frame is far below a pixel
DELTA = 0.13             # hue step per level
LENS = 35.0
SCREEN_W, SCREEN_H = 0.40, 0.30   # 4:3 hole, same aspect as the render
ZS = 0.62                # screen centre height; screen plane is y = 0, centre x = 0
EPS = 0.004              # nested worlds sit just inside the hole
TAN_H = 18.0 / LENS      # half horizontal FOV tangent for a 36 mm sensor
TAN_V = TAN_H * 3 / 4
D0 = SCREEN_W / S_LEVEL / (2 * TAN_H)     # camera distance at t = 0
WALL_Y = 1.13
APEX_Y = EPS - S_LEVEL * D0               # where the scaled camera sits: the cavity flares from here


def frustum_half(y):
    """Half width/height of the level-0 view at plane y (distance D0 + y from the camera)."""
    return (D0 + y) * TAN_H, (D0 + y) * TAN_V


def _tilt(x, y, z):
    """Rotate a point by THETA about the viewing axis through the screen centre (same rotation as M)."""
    v = Matrix.Rotation(THETA, 3, "Y") @ Vector((x, 0.0, z - ZS))
    return (v.x, y, v.z + ZS)


def console_tv(mats):
    """Cabinet whose screen hole is M(view rectangle): tilted by THETA, with a cavity that flares along the
    nested camera's frustum, so every deeper level fills the hole exactly."""
    bm = bmesh.new()
    x0, x1, z0, z1, y1 = -0.54, 0.66, 0.15, 1.09, 0.50
    hw, hh = SCREEN_W / 2, SCREEN_H / 2
    dmax = 0.37
    WOOD, CAV, METAL = 0, 1, 2

    def quad(pts, mat):
        bm.faces.new([bm.verts.new(p) for p in pts]).material_index = mat

    outer = [(x0, 0, z0), (x1, 0, z0), (x1, 0, z1), (x0, 0, z1)]
    front = [_tilt(-hw, 0, ZS - hh), _tilt(hw, 0, ZS - hh), _tilt(hw, 0, ZS + hh), _tilt(-hw, 0, ZS + hh)]
    for i in range(4):  # front face: ring between the cabinet outline and the tilted hole
        j = (i + 1) % 4
        quad([outer[i], outer[j], front[j], front[i]], WOOD)
    quad([(x1, 0, z0), (x1, y1, z0), (x1, y1, z1), (x1, 0, z1)], WOOD)
    quad([(x0, y1, z0), (x0, 0, z0), (x0, 0, z1), (x0, y1, z1)], WOOD)
    quad([(x0, 0, z1), (x1, 0, z1), (x1, y1, z1), (x0, y1, z1)], WOOD)
    quad([(x0, y1, z0), (x1, y1, z0), (x1, 0, z0), (x0, 0, z0)], WOOD)
    quad([(x1, y1, z0), (x0, y1, z0), (x0, y1, z1), (x1, y1, z1)], WOOD)
    f = (dmax - APEX_Y) / (0 - APEX_Y)  # cavity walls run along lines from the nested camera
    back = [_tilt(-hw * f, dmax, ZS - hh * f), _tilt(hw * f, dmax, ZS - hh * f),
            _tilt(hw * f, dmax, ZS + hh * f), _tilt(-hw * f, dmax, ZS + hh * f)]
    for i in range(4):
        j = (i + 1) % 4
        quad([front[i], back[i], back[j], front[j]], CAV)
    quad(back[::-1], CAV)
    for i in range(7):  # speaker grille, knobs, legs, rabbit ears
        props._assign(bm, props._box(bm, (0.56, -0.003, 0.3 + i * 0.07), (0.14, 0.006, 0.022)), METAL)
    for kz in (0.95, 0.84):
        props._assign(bm, props._tube(bm, (0.56, 0, kz), (0.56, -0.03, kz), 0.03, 16), METAL)
    for lx in (-0.48, 0.6):
        for ly in (0.06, 0.44):
            props._assign(bm, props._tube(bm, (lx, ly, z0), (lx * 1.04, ly, 0.0), 0.018), WOOD)
    for ax in (-1, 1):
        props._assign(bm, props._tube(bm, (0.05, 0.25, z1), (0.05 + ax * 0.25, 0.3, z1 + 0.4), 0.006), METAL)
    return props._finish(bm, "console_tv", [mats["tv"], mats["cavity"], mats["metal"]])


def build(ctx):
    world = bpy.context.scene.world
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (0, 0, 0, 1)
    bg.inputs["Strength"].default_value = 0.0
    bpy.context.scene.camera.data.sensor_fit = "HORIZONTAL"
    bpy.context.scene.camera.data.sensor_width = 36.0

    mats = {
        "tv": looks.flat_emissive(assets.texture_material(ctx, "tv", (0.35, 0.2, 0.1)), "FLAT_tv"),
        "cavity": looks.flat_emissive((0.02, 0.02, 0.03), "FLAT_cavity", facing_shade=0.0),
        "metal": looks.flat_emissive((0.8, 0.8, 0.85), "FLAT_metal"),
        "wall": looks.flat_emissive(assets.texture_material(ctx, "wall", (0.6, 0.3, 0.5)), "FLAT_wall", 1.0, 0.2),
        "floor": looks.flat_emissive(assets.texture_material(ctx, "floor", (0.3, 0.3, 0.5)), "FLAT_floor", 1.0, 0.2),
    }
    base = {}
    base["tv"] = (console_tv(mats), 0.07)
    wx, wz = frustum_half(WALL_Y)
    wall = geo.mesh_object("wall", [(-wx, WALL_Y, ZS - wz), (wx, WALL_Y, ZS - wz), (wx, WALL_Y, ZS + wz),
                                    (-wx, WALL_Y, ZS + wz)], [(0, 1, 2, 3)], smooth=False,
                           uvs=[(-wx / 0.6, -wz / 0.6), (wx / 0.6, -wz / 0.6), (wx / 0.6, wz / 0.6),
                                (-wx / 0.6, wz / 0.6)])
    wall.data.materials.append(mats["wall"])
    base["wall"] = (wall, 0.85)
    y_near = (ZS / TAN_V) - D0 + 0.01  # floor enters the view here; anything nearer would never be seen
    nx, _ = frustum_half(y_near)
    fx, _ = frustum_half(WALL_Y)
    floor_pts = [(-nx, y_near, 0), (nx, y_near, 0), (fx, WALL_Y, 0), (-fx, WALL_Y, 0)]
    floor = geo.mesh_object("floor", floor_pts, [(0, 1, 2, 3)], smooth=False,
                            uvs=[(p[0] / 0.8, p[1] / 0.8) for p in floor_pts])
    floor.data.materials.append(mats["floor"])
    base["floor"] = (floor, 0.6)
    chair = assets.load_model(ctx, "chair", 0.75)
    if chair:
        for i, slot in enumerate(chair.material_slots):
            slot.material = looks.flat_emissive(slot.material or (0.7, 0.7, 0.7), f"FLAT_chair_{i}")
    else:
        chair = props.lawn_chair()
        chair.data.materials[0] = mats["metal"]
        chair.data.materials[1] = looks.flat_emissive((0.9, 0.5, 0.2), "FLAT_webbing")
    chair.matrix_world = Matrix.Translation((0.7, 0.8, 0.0)) @ Matrix.Rotation(math.radians(-35), 4, "Z")
    base["chair"] = (chair, 0.33)

    a = Vector((0.0, EPS / (1 - S_LEVEL), ZS))  # fixed point of M
    levels = []
    for k in range(LEVELS):
        m = (Matrix.Translation(a) @ Matrix.Rotation(THETA * k, 4, "Y") @ Matrix.Scale(S_LEVEL ** k, 4)
             @ Matrix.Translation(-a))
        for name, (src, hue) in base.items():
            obj = src if k == 0 else geo.link_copy(src, bpy.context.scene.collection, f"{name}_L{k}")
            obj.matrix_world = m @ src.matrix_world if k else src.matrix_world.copy()
            levels.append((obj, k, hue))
    # Base objects keep their own matrices; copies were placed relative to them above.
    return {"levels": levels, "fixed": a, "start": Vector((0.0, -D0, ZS))}


def frame(ctx, st, t, f):
    for obj, k, hue in st["levels"]:
        obj.color = looks.hsv(hue + DELTA * (k - t), 0.55, 1.0)
    a, c0 = st["fixed"], st["start"]
    eye = a + (S_LEVEL ** t) * (c0 - a)
    cam = bpy.context.scene.camera
    look = Matrix.Rotation(THETA * t, 4, "Y") @ Matrix.Rotation(math.pi / 2, 4, "X")  # base pose looks along +Y
    cam.matrix_world = Matrix.Translation(eye) @ look
    cam.data.lens = LENS
    cam.data.clip_start = 0.0005
    cam.data.clip_end = 100
