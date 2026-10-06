"""A 4D quaternion Julia set, sliced into 3D and re-meshed every frame, covered in hairy googly-eyed blobs.

q -> q^2 + c over quaternions. The 3D slice sits at w = 0.22 sin(2 pi t) and c walks a small closed loop,
so the fractal morphs and returns exactly to its first shape. The surface comes from marching cubes on
a log|q| escape field (scikit-image, installed into BlenderProc's Blender with ``blenderproc pip``).
Furry blobs ("tribbles", one hair system instanced as a collection) cling to the surface: each is pinned
to the nearest surface point of a fixed anchor direction, so they glide continuously as the shape morphs.
"""

import math

import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.kdtree import KDTree

from fever.core import geo, looks, props
from fever.core.assets import World

SCENE = {
    "id": "hairy_julia",
    "title": "Hairy Julia",
    "logline": "A four-dimensional quaternion Julia set, sliced through a moving hyperplane and furred with "
               "googly-eyed blobs that ride its mutating surface.",
    "seconds": 12,
    "fps": 24,
    "shards": 12,
    "haven": {"hdris": {"world": ["night", "studio", "dark", "neon"]}},
}

TAU = 2 * math.pi
C0 = np.array([-0.291, -0.399, 0.339, 0.437])
BOUND = 1.45


def julia_field(t, n):
    """log|q| after 12 iterations on an n^3 grid, for the 3D slice of the 4D set at loop time t."""
    from skimage import measure  # noqa: F401  (imported here so a missing package fails loudly at build)
    c = C0 + 0.05 * np.array([math.cos(TAU * t), math.sin(TAU * t), math.sin(TAU * t), math.cos(TAU * t)])
    w = 0.22 * math.sin(TAU * t)
    axis = np.linspace(-BOUND, BOUND, n)
    x, y, z = np.meshgrid(axis, axis, axis, indexing="ij")
    q = np.stack([x, y, z, np.full_like(x, w)], 0).reshape(4, -1)
    mag2 = np.zeros(q.shape[1])
    alive = np.ones(q.shape[1], bool)
    for _ in range(12):
        a, b, cc, d = q[:, alive]
        q[:, alive] = np.stack([a * a - b * b - cc * cc - d * d + c[0], 2 * a * b + c[1], 2 * a * cc + c[2],
                                2 * a * d + c[3]])
        mag2[alive] = np.sum(q[:, alive] ** 2, 0)
        alive &= mag2 < 256.0
    return np.log(np.maximum(mag2, 1e-12)).reshape(n, n, n), axis[1] - axis[0]


def surface(t, n):
    from skimage import measure
    field, h = julia_field(t, n)
    level = math.log(4.0)  # |q| = 2
    if not field.min() < level < field.max():
        return None, None
    verts, faces, _, _ = measure.marching_cubes(field, level)
    return verts * h - BOUND, faces


def build(ctx):
    world = World(ctx, strength=0.35, fallback=((0.02, 0.0, 0.05), (0.2, 0.05, 0.35)))
    fractal = geo.mesh_object("julia", [(0, 0, 0)], [], smooth=True)
    mat = looks.iridescent("MAT_julia")
    tribe = geo.new_collection("TRIBBLE", linked=False)
    props.tribble(tribe, hairs=ctx.count(900, 200))
    anchors = geo.fibonacci_sphere(ctx.count(260, 50)) * 1.8
    rng = ctx.rng(3)
    holders = []
    for i in range(len(anchors)):
        e = bpy.data.objects.new(f"tribble_{i}", None)
        e.instance_type = "COLLECTION"
        e.instance_collection = tribe
        bpy.context.scene.collection.objects.link(e)
        holders.append((e, 1.6 + 2.0 * rng.random(), rng.random()))
    for i in range(3):  # coloured key lights
        light = bpy.data.lights.new(f"key_{i}", "AREA")
        light.energy, light.size = 250, 1.5
        light.color = looks.hsv(i / 3, 0.7)[:3]
        obj = bpy.data.objects.new(f"key_{i}", light)
        a = TAU * i / 3
        obj.matrix_world = geo.look_at(np.array([3.5 * math.cos(a), 3.5 * math.sin(a), 1.5]), np.zeros(3))
        bpy.context.scene.collection.objects.link(obj)
    grid = int(np.clip(round(96 * ctx.detail ** 0.5), 40, 112))
    return {"world": world, "fractal": fractal, "mat": mat, "anchors": anchors, "holders": holders, "grid": grid}


def frame(ctx, st, t, f):
    st["world"].set(hue_shift=t, saturation=1.3)
    verts, faces = surface(t, st["grid"])
    obj = st["fractal"]
    old = obj.data
    if verts is None:
        mesh = bpy.data.meshes.new("julia")
    else:
        mesh = bpy.data.meshes.new("julia")
        mesh.from_pydata(verts.tolist(), [], faces.tolist())
        mesh.polygons.foreach_set("use_smooth", [True] * len(mesh.polygons))
        mesh.update()
    mesh.materials.append(st["mat"])
    obj.data = mesh
    bpy.data.meshes.remove(old)
    obj.rotation_euler = (0.0, 0.0, TAU * t)  # the whole set turns once per loop
    rot = Matrix.Rotation(TAU * t, 3, "Z")  # matrix_world isn't re-evaluated until the depsgraph updates

    if verts is None or len(verts) == 0:
        for e, _, _ in st["holders"]:
            e.hide_render = True
        return
    tree = KDTree(len(verts))
    for i, v in enumerate(verts):
        tree.insert(v, i)
    tree.balance()
    normals = np.empty(len(mesh.vertices) * 3)
    mesh.vertices.foreach_get("normal", normals)
    normals = normals.reshape(-1, 3)
    for (e, size, phase), anchor in zip(st["holders"], st["anchors"]):
        co, idx, _ = tree.find(anchor)
        n = Vector(normals[idx]).normalized()
        pos = rot @ (Vector(co) + n * 0.02)
        breathe = 0.75 + 0.25 * math.sin(TAU * (2 * t + phase))
        orient = (rot @ n).to_track_quat("Z", "Y").to_matrix().to_4x4()
        e.matrix_world = Matrix.Translation(pos) @ orient @ Matrix.Diagonal((*(3 * [size * breathe]), 1))
        e.hide_render = False
    a = TAU * t
    eye = np.array([3.4 * math.cos(-a), 3.4 * math.sin(-a), 1.1 * math.sin(a)])  # one orbit per loop
    geo.set_camera(eye, np.zeros(3), lens=40)
