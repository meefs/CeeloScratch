"""Procedural props: things Poly Haven doesn't have, and stand-ins for when a model wasn't downloaded."""

import math

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

from fever.core import looks
from fever.core.geo import mesh_object

TAU = 2 * math.pi


def _tube(bm, p0, p1, r, segments=8):
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    m = Matrix.Translation((p0 + p1) / 2) @ d.to_track_quat("Z", "Y").to_matrix().to_4x4()
    return bmesh.ops.create_cone(bm, cap_ends=True, segments=segments, radius1=r, radius2=r, depth=d.length,
                                 matrix=m)["verts"]


def _box(bm, center, size, rot=None):
    m = Matrix.Translation(center) @ (rot or Matrix.Identity(4)) @ Matrix.Diagonal((*size, 1))
    return bmesh.ops.create_cube(bm, size=1.0, matrix=m)["verts"]


def _assign(bm, verts, index):
    for f in {f for v in verts for f in v.link_faces}:
        f.material_index = index


def _finish(bm, name, materials, collection=None, smooth=False):
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    if smooth:
        mesh.polygons.foreach_set("use_smooth", [True] * len(mesh.polygons))
    for m in materials:
        mesh.materials.append(m)
    obj = bpy.data.objects.new(name, mesh)
    (collection or bpy.context.scene.collection).objects.link(obj)
    return obj


def lawn_chair(collection=None):
    """Classic folding aluminium lawn chair with woven webbing; webbing colour comes from obj.color."""
    bm = bmesh.new()
    alu, web = [], []
    r = 0.011
    for x in (-0.24, 0.24):  # side frames: legs, seat rail, back rail, arm rest
        alu += _tube(bm, (x, 0.28, 0.0), (x, -0.22, 0.42), r)
        alu += _tube(bm, (x, -0.24, 0.0), (x, 0.20, 0.40), r)
        alu += _tube(bm, (x, -0.25, 0.40), (x, 0.24, 0.40), r)
        alu += _tube(bm, (x, 0.24, 0.40), (x, 0.36, 0.86), r)
        alu += _tube(bm, (x, -0.22, 0.62), (x, 0.26, 0.62), r * 1.2)
    for y, z in ((-0.25, 0.40), (0.24, 0.40), (0.36, 0.86)):
        alu += _tube(bm, (-0.24, y, z), (0.24, y, z), r)
    seat_tilt = Matrix.Rotation(math.radians(4), 4, "X")
    back_tilt = Matrix.Rotation(math.radians(-14), 4, "X")
    for i in range(6):  # seat straps run front to back, back straps run side to side
        web += _box(bm, (-0.2 + i * 0.08, 0.0, 0.405), (0.06, 0.5, 0.008), seat_tilt)
    for i in range(6):
        web += _box(bm, (0.0, 0.25 + i * 0.022, 0.46 + i * 0.075), (0.5, 0.008, 0.055), back_tilt)
    _assign(bm, alu, 0)
    _assign(bm, web, 1)
    return _finish(bm, "lawn_chair", [looks.principled("MAT_aluminium", (0.8, 0.82, 0.85), 0.25, 1.0),
                                       looks.object_color("MAT_webbing", roughness=0.6, sheen=0.4)], collection)


def cowboy_hat(collection=None, segments=48):
    """Revolved cowboy hat: creased oval crown, brim curling up at the sides, glowing band (material 1)."""
    profile = [(0.0, 0.112), (0.03, 0.122), (0.058, 0.132), (0.078, 0.128), (0.088, 0.112), (0.092, 0.07),
               (0.094, 0.03), (0.095, 0.0), (0.112, -0.002), (0.135, 0.0), (0.158, 0.008), (0.175, 0.02)]
    verts, faces = [], []
    for j in range(segments):
        u = TAU * j / segments
        cu, su = math.cos(u), math.sin(u)
        for (r, z) in profile:
            crown = r <= 0.095
            ex, ey = (1.0, 1.16) if crown else (1.0, 1.08)
            zz = z
            if crown and z > 0.09:
                zz -= 0.012 * max(0.0, su)  # front pinch
            if not crown:
                zz += 0.9 * (r - 0.095) ** 1.25 * cu * cu  # brim curls up at the sides
            verts.append((r * cu * ex, r * su * ey, zz))
    n = len(profile)
    for j in range(segments):
        jn = (j + 1) % segments
        for i in range(n - 1):
            faces.append((j * n + i, jn * n + i, jn * n + i + 1, j * n + i + 1))
    obj = mesh_object("cowboy_hat", verts, faces, collection, smooth=True)
    band = [(0.0965, 0.0), (0.0965, 0.02)]
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    base = len(bm.verts)
    bverts = [bm.verts.new((band[k][0] * math.cos(TAU * j / segments),
                            band[k][0] * math.sin(TAU * j / segments) * 1.16, band[k][1]))
              for j in range(segments) for k in range(2)]
    bm.verts.ensure_lookup_table()
    for j in range(segments):
        jn = (j + 1) % segments
        f = bm.faces.new((bverts[2 * j], bverts[2 * jn], bverts[2 * jn + 1], bverts[2 * j + 1]))
        f.material_index = 1
        f.smooth = True
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.materials.append(looks.object_color("MAT_felt", roughness=0.85, coat=0.0, sheen=0.6))
    obj.data.materials.append(looks.principled("MAT_hatband", (0.9, 0.7, 0.2), 0.3, 0.6,
                                               emission=(1.0, 0.4, 0.9), strength=2.5))
    solid = obj.modifiers.new("felt", "SOLIDIFY")
    solid.thickness = 0.004
    return obj


WING_OUTLINE = [(0.0, 0.15), (0.35, 0.45), (0.75, 0.62), (0.95, 0.55), (0.9, 0.25), (0.6, 0.05),
                (0.75, -0.15), (0.7, -0.45), (0.45, -0.6), (0.2, -0.45), (0.0, -0.2)]


def butterfly_parts(collection, half_span=0.05):
    """Body plus right/left wing meshes; wings hinge on the body's local Y axis (x=0)."""
    mat = looks.butterfly_wing("MAT_wing")
    parts = {}
    for side, sign in (("R", 1.0), ("L", -1.0)):
        pts = [(0.0, 0.0)] + WING_OUTLINE
        verts = [(sign * x * half_span, y * half_span, 0.0) for x, y in pts]
        faces = [(0, i, i + 1) if sign > 0 else (0, i + 1, i) for i in range(1, len(pts) - 1)]
        uvs = [(x, (y + 0.65) / 1.3) for x, y in pts]
        wing = mesh_object(f"wing_{side}", verts, faces, collection, smooth=False, uvs=uvs)
        wing.data.materials.append(mat)
        parts[side] = wing
    bm = bmesh.new()
    _tube(bm, (0, -0.6 * half_span, 0), (0, 0.6 * half_span, 0), 0.07 * half_span, 6)
    parts["body"] = _finish(bm, "butterfly_body", [looks.principled("MAT_thorax", (0.03, 0.02, 0.02), 0.5)],
                            collection, smooth=True)
    return parts


def crt_tv(materials, collection=None):
    """Wood-cabinet CRT with an open screen (a hole into a dark cavity) so nested worlds can sit inside.

    materials: dict with 'wood', 'cavity', 'metal'. Returns (object, screen) where screen holds the
    hole's centre (x, z), width, height and the front-face plane y (the TV faces -Y).
    """
    W, D, H = 0.64, 0.46, 0.50
    sw, sh = 0.40, 0.30
    cx, cz = -0.07, 0.27
    y0 = -D / 2
    bm = bmesh.new()
    x0, x1, z0, z1 = -W / 2, W / 2, 0.02, 0.02 + H
    hx0, hx1, hz0, hz1 = cx - sw / 2, cx + sw / 2, cz - sh / 2, cz + sh / 2
    WOOD, CAV, METAL = 0, 1, 2

    def quad(a, b, c, d, mat):
        bm.faces.new([bm.verts.new(p) for p in (a, b, c, d)]).material_index = mat

    def part(verts, mat):
        _assign(bm, verts, mat)

    # Front frame around the hole (normals facing -Y).
    quad((x0, y0, z0), (x1, y0, z0), (x1, y0, hz0), (x0, y0, hz0), WOOD)
    quad((x0, y0, hz1), (x1, y0, hz1), (x1, y0, z1), (x0, y0, z1), WOOD)
    quad((x0, y0, hz0), (hx0, y0, hz0), (hx0, y0, hz1), (x0, y0, hz1), WOOD)
    quad((hx1, y0, hz0), (x1, y0, hz0), (x1, y0, hz1), (hx1, y0, hz1), WOOD)
    # Other five faces of the cabinet.
    y1 = D / 2
    quad((x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1), WOOD)
    quad((x0, y1, z0), (x0, y0, z0), (x0, y0, z1), (x0, y1, z1), WOOD)
    quad((x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1), WOOD)
    quad((x0, y1, z0), (x1, y1, z0), (x1, y0, z0), (x0, y0, z0), WOOD)
    quad((x1, y1, z0), (x0, y1, z0), (x0, y1, z1), (x1, y1, z1), WOOD)
    # Cavity behind the hole (inward-facing walls).
    yb = y1 - 0.03
    quad((hx0, y0, hz0), (hx0, yb, hz0), (hx1, yb, hz0), (hx1, y0, hz0), CAV)
    quad((hx0, yb, hz1), (hx0, y0, hz1), (hx1, y0, hz1), (hx1, yb, hz1), CAV)
    quad((hx0, y0, hz1), (hx0, yb, hz1), (hx0, yb, hz0), (hx0, y0, hz0), CAV)
    quad((hx1, yb, hz1), (hx1, y0, hz1), (hx1, y0, hz0), (hx1, yb, hz0), CAV)
    quad((hx0, yb, hz0), (hx0, yb, hz1), (hx1, yb, hz1), (hx1, yb, hz0), CAV)
    # Knobs, speaker grille bars, legs and rabbit-ear antennae (material set as each part is made).
    for kz in (0.36, 0.22):
        part(_tube(bm, (0.22, y0, kz), (0.22, y0 - 0.025, kz), 0.025, 16), METAL)
    for i in range(5):
        part(_box(bm, (0.22, y0 - 0.002, 0.12 - i * 0.018 + 0.05), (0.09, 0.004, 0.006)), METAL)
    for lx in (-0.26, 0.26):
        for ly in (-0.16, 0.16):
            part(_tube(bm, (lx, ly, 0.02), (lx * 1.08, ly * 1.08, -0.22), 0.015), WOOD)
    for ax in (-1, 1):
        part(_tube(bm, (0.05, 0.05, z1), (0.05 + ax * 0.22, 0.12, z1 + 0.42), 0.005), METAL)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    obj = _finish(bm, "crt_tv", [materials["wood"], materials["cavity"], materials["metal"]], collection)
    return obj, {"cx": cx, "cz": cz, "w": sw, "h": sh, "y": y0, "depth": yb - y0}


def bust_fallback(collection=None):
    """Stand-in classical bust (0.75 m): head, neck and shoulders, if no Poly Haven bust was available."""
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=16, radius=0.1,
                              matrix=Matrix.Translation((0, 0, 0.62)) @ Matrix.Diagonal((0.85, 1.0, 1.15, 1)))
    _tube(bm, (0, 0, 0.42), (0, 0, 0.56), 0.05, 16)
    bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=16, radius=0.22,
                              matrix=Matrix.Translation((0, 0, 0.2)) @ Matrix.Diagonal((1.0, 0.55, 0.9, 1)))
    _tube(bm, (0, 0, 0.0), (0, 0, 0.12), 0.17, 24)
    return _finish(bm, "bust", [looks.principled("MAT_plaster_bust", (0.92, 0.9, 0.86), 0.35, coat=0.3)],
                   collection, smooth=True)


def tribble(collection, hairs=900, radius=0.045):
    """A hairy googly-eyed blob: particle hair coloured per instance (Object Info > Random)."""
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=3, radius=radius)
    body = _finish(bm, "tribble", [], collection, smooth=True)
    hair_mat = bpy.data.materials.new("MAT_tribble_hair")
    hair_mat.use_nodes = True
    nt = hair_mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    hair = nt.nodes.new("ShaderNodeBsdfHairPrincipled")
    hair.parametrization = "COLOR"
    info = nt.nodes.new("ShaderNodeObjectInfo")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    els = ramp.color_ramp.elements
    els[0].color, els[1].color = looks.hsv(0.9, 0.9), looks.hsv(0.5, 0.9)
    els.new(0.5).color = looks.hsv(0.15, 0.95)
    nt.links.new(info.outputs["Random"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], hair.inputs["Color"])
    nt.links.new(hair.outputs["BSDF"], out.inputs["Surface"])
    body.data.materials.append(looks.principled("MAT_tribble_skin", (0.2, 0.1, 0.2), 0.8))
    body.data.materials.append(hair_mat)
    mod = body.modifiers.new("fur", "PARTICLE_SYSTEM")
    ps = mod.particle_system.settings
    ps.type = "HAIR"
    ps.count = hairs
    ps.hair_length = radius * 1.4
    ps.material = 2
    ps.render_step = 3
    ps.use_advanced_hair = True
    ps.root_radius = 0.0012
    ps.tip_radius = 0.0002
    mod.particle_system.seed = 7
    eye_w = looks.principled("MAT_eye_white", (1, 1, 1), 0.2, coat=1.0)
    eye_b = looks.principled("MAT_pupil", (0.0, 0.0, 0.0), 0.1, coat=1.0)
    eyes = bmesh.new()
    for ex in (-0.35, 0.35):
        c = Vector((ex * radius, -0.85 * radius, 0.45 * radius))
        bmesh.ops.create_uvsphere(eyes, u_segments=16, v_segments=8, radius=radius * 0.32,
                                  matrix=Matrix.Translation(c))
    pupils = bmesh.new()
    for ex in (-0.35, 0.35):
        c = Vector((ex * radius, -1.1 * radius, 0.45 * radius))
        bmesh.ops.create_uvsphere(pupils, u_segments=12, v_segments=6, radius=radius * 0.14,
                                  matrix=Matrix.Translation(c))
    _finish(eyes, "tribble_eyes", [eye_w], collection, smooth=True)
    _finish(pupils, "tribble_pupils", [eye_b], collection, smooth=True)
    return body


def sphere(name, radius, material, collection=None, segments=24):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=segments // 2, radius=radius)
    return _finish(bm, name, [material], collection, smooth=True)
