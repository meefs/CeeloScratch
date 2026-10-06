"""Geometry helpers: camera look-at (via BlenderProc), object bases, curves, frames, meshes from numpy."""

import math

import blenderproc as bproc
import bpy
import numpy as np
from mathutils import Matrix, Vector

TAU = 2 * math.pi


def look_at(eye, target, roll=0.0):
    """4x4 camera-to-world matrix looking from eye to target (BlenderProc's camera maths)."""
    forward = np.asarray(target, float) - np.asarray(eye, float)
    rotation = bproc.camera.rotation_from_forward_vec(forward, inplane_rot=roll)
    return Matrix(bproc.math.build_transformation_mat(np.asarray(eye, float), rotation).tolist())


def set_camera(eye, target, roll=0.0, lens=None):
    cam = bpy.context.scene.camera
    cam.matrix_world = look_at(eye, target, roll)
    if lens:
        cam.data.lens = lens
    cam.data.clip_start = 0.02
    cam.data.clip_end = 500


def basis(x_axis, y_axis, z_axis, location, scale=1.0):
    """World matrix from three (not necessarily normalised) axes, a location and a uniform scale."""
    x, y, z = (np.asarray(v, float) for v in (x_axis, y_axis, z_axis))
    x, y, z = x / np.linalg.norm(x), y / np.linalg.norm(y), z / np.linalg.norm(z)
    m = np.identity(4)
    m[:3, 0], m[:3, 1], m[:3, 2] = x * scale, y * scale, z * scale
    m[:3, 3] = location
    return Matrix(m.tolist())


def orthonormal(forward, up=(0.0, 0.0, 1.0)):
    """Right, forward, up unit vectors for a heading, keeping 'up' as close to the given up as possible."""
    f = np.asarray(forward, float)
    f = f / (np.linalg.norm(f) + 1e-12)
    u = np.asarray(up, float)
    r = np.cross(f, u)
    if np.linalg.norm(r) < 1e-6:
        r = np.cross(f, (1.0, 0.0, 0.0))
    r = r / np.linalg.norm(r)
    u = np.cross(r, f)
    return r, f, u


def rotate_about(v, axis, angle):
    """Rodrigues rotation of vectors v (..., 3) about unit axes (..., 3)."""
    c, s = np.cos(angle)[..., None], np.sin(angle)[..., None]
    return v * c + np.cross(axis, v) * s + axis * np.sum(axis * v, -1, keepdims=True) * (1 - c)


def resample_closed(points, n):
    """Resample a closed polyline to n points evenly spaced by arc length."""
    closed = np.vstack([points, points[:1]])
    seg = np.linalg.norm(np.diff(closed, axis=0), axis=1)
    s = np.concatenate([[0.0], np.cumsum(seg)])
    target = np.linspace(0.0, s[-1], n, endpoint=False)
    out = np.stack([np.interp(target, s, closed[:, k]) for k in range(3)], 1)
    return out, s[-1]


def frames_closed(points):
    """Tangent/normal/binormal frames along a closed curve by parallel transport, twist-corrected to close."""
    n = len(points)
    t = np.roll(points, -1, 0) - np.roll(points, 1, 0)
    t /= np.linalg.norm(t, axis=1, keepdims=True)
    nrm = np.zeros_like(t)
    a = np.cross(t[0], (0.0, 0.0, 1.0))
    if np.linalg.norm(a) < 1e-6:
        a = np.cross(t[0], (1.0, 0.0, 0.0))
    nrm[0] = a / np.linalg.norm(a)
    for i in range(1, n):
        v = nrm[i - 1] - np.dot(nrm[i - 1], t[i]) * t[i]
        nrm[i] = v / np.linalg.norm(v)
    # Transport the last normal back to the start and spread the leftover twist evenly.
    v = nrm[-1] - np.dot(nrm[-1], t[0]) * t[0]
    v /= np.linalg.norm(v)
    twist = math.atan2(np.dot(np.cross(v, nrm[0]), t[0]), np.dot(v, nrm[0]))
    nrm = rotate_about(nrm, t, np.linspace(0.0, twist, n, endpoint=False))
    return t, nrm, np.cross(t, nrm)


def torus_knot(p, q, big_r, small_r, u):
    u = np.asarray(u, float)
    rr = big_r + small_r * np.cos(q * u)
    return np.stack([rr * np.cos(p * u), rr * np.sin(p * u), small_r * np.sin(q * u)], -1)


def lorenz(steps, dt=0.004, warmup=2000, sigma=10.0, rho=28.0, beta=8.0 / 3.0):
    """Lorenz attractor trajectory (RK4)."""
    def f(s):
        x, y, z = s
        return np.array([sigma * (y - x), x * (rho - z) - y, x * y - beta * z])

    s = np.array([1.0, 1.0, 1.0])
    out = np.empty((steps, 3))
    for i in range(warmup + steps):
        k1 = f(s)
        k2 = f(s + 0.5 * dt * k1)
        k3 = f(s + 0.5 * dt * k2)
        k4 = f(s + dt * k3)
        s = s + dt / 6 * (k1 + 2 * k2 + 2 * k3 + k4)
        if i >= warmup:
            out[i - warmup] = s
    return out


def fibonacci_sphere(n):
    i = np.arange(n) + 0.5
    phi = np.arccos(1 - 2 * i / n)
    theta = math.pi * (1 + 5 ** 0.5) * i
    return np.stack([np.cos(theta) * np.sin(phi), np.sin(theta) * np.sin(phi), np.cos(phi)], 1)


def mesh_object(name, verts, faces, collection=None, smooth=True, uvs=None):
    """Create (or rebuild) a mesh object from numpy vertex/face arrays."""
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(np.asarray(verts, float).tolist(), [], np.asarray(faces, int).tolist())
    if smooth:
        mesh.polygons.foreach_set("use_smooth", [True] * len(mesh.polygons))
    if uvs is not None:
        layer = mesh.uv_layers.new(name="UVMap")
        loop_vert = np.zeros(len(mesh.loops), dtype=np.int64)
        mesh.loops.foreach_get("vertex_index", loop_vert)
        layer.data.foreach_set("uv", np.asarray(uvs, float)[loop_vert].ravel())
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    (collection or bpy.context.scene.collection).objects.link(obj)
    return obj


def grid_plane(name, size_x, size_y, tile, collection=None, segments=1):
    """Flat plane centred at the origin with UVs in world units / tile (so textures tile at real scale)."""
    xs = np.linspace(-size_x / 2, size_x / 2, segments + 1)
    ys = np.linspace(-size_y / 2, size_y / 2, segments + 1)
    gx, gy = np.meshgrid(xs, ys)
    verts = np.stack([gx.ravel(), gy.ravel(), np.zeros(gx.size)], 1)
    w = segments + 1
    faces = [(j * w + i, j * w + i + 1, (j + 1) * w + i + 1, (j + 1) * w + i)
             for j in range(segments) for i in range(segments)]
    return mesh_object(name, verts, faces, collection, smooth=False, uvs=verts[:, :2] / tile)


def link_copy(src, collection, name=None):
    """A new object sharing src's mesh data (cheap instancing that Cycles shares in memory)."""
    obj = src.copy()
    if name:
        obj.name = name
    obj.hide_render = False
    obj.hide_viewport = False
    collection.objects.link(obj)
    return obj


def new_collection(name, parent=None, linked=True):
    coll = bpy.data.collections.new(name)
    if linked:
        (parent or bpy.context.scene.collection).children.link(coll)
    return coll


def camera_basis(eye, forward, up, lens=None):
    """Place the camera at eye, looking along forward, with its top edge as close to 'up' as possible."""
    f = np.asarray(forward, float)
    f = f / np.linalg.norm(f)
    u = np.asarray(up, float) - np.dot(up, f) * f
    u = u / np.linalg.norm(u)
    cam = bpy.context.scene.camera
    cam.matrix_world = basis(np.cross(f, u), u, -f, eye)
    if lens:
        cam.data.lens = lens
    cam.data.clip_start = 0.02
    cam.data.clip_end = 500


def along_closed(points, u):
    """Linearly interpolated point on a closed, evenly sampled curve at fraction u of the way round."""
    n = len(points)
    x = (u % 1.0) * n
    i0 = int(math.floor(x)) % n
    frac = x - math.floor(x)
    return points[i0] * (1 - frac) + points[(i0 + 1) % n] * frac
