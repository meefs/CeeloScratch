# Step 4 - rainbow sprinkles scattered over the top of the icing, lying flat, never overlapping.
import itertools
import math
import random

import bmesh
import bpy
from mathutils import Matrix, Vector

asset = bpy.data.collections["ASSET_" + PARAMS["asset_name"]]
icing = bpy.data.objects["donut_icing"]
rng = random.Random(PARAMS["seed"])

COUNT = PARAMS.get("sprinkle_count", 260)
LENGTH, RADIUS = 0.0060, 0.00085
COLORS = {
    "white":    (0.95, 0.95, 0.92, 1.0),
    "lemon":    (0.98, 0.83, 0.12, 1.0),
    "sky":      (0.18, 0.55, 0.95, 1.0),
    "mint":     (0.25, 0.85, 0.55, 1.0),
    "tangerine": (0.98, 0.45, 0.08, 1.0),
    "grape":    (0.50, 0.25, 0.85, 1.0),
}

# Sample the evaluated (solidified + subdivided) icing so sprinkles sit on the real surface.
depsgraph = bpy.context.evaluated_depsgraph_get()
evaluated = icing.evaluated_get(depsgraph)
surface = evaluated.to_mesh()
surface.calc_loop_triangles()
mw = icing.matrix_world
tris, weights = [], []
for tri in surface.loop_triangles:
    normal = (mw.to_3x3() @ tri.normal).normalized()
    if normal.z > 0.45:  # only the upward-facing top layer
        tris.append((tuple(tri.vertices), normal))
        weights.append(tri.area)
verts = [mw @ v.co for v in surface.vertices]
cum_weights = list(itertools.accumulate(weights))

placed = []
attempts = 0
while len(placed) < COUNT and attempts < COUNT * 40:
    attempts += 1
    tri, normal = rng.choices(tris, cum_weights=cum_weights)[0]
    a, b, c = (verts[i] for i in tri)
    r1, r2 = rng.random(), rng.random()
    if r1 + r2 > 1.0:
        r1, r2 = 1.0 - r1, 1.0 - r2
    point = a + (b - a) * r1 + (c - a) * r2
    if any((point - p).length < LENGTH * 0.75 for p, _n in placed):
        continue
    placed.append((point, normal))
evaluated.to_mesh_clear()

bm = bmesh.new()
color_names = list(COLORS)
for point, normal in placed:
    # Random direction in the tangent plane becomes the sprinkle's long axis.
    helper = Vector((0, 0, 1)) if abs(normal.z) < 0.9 else Vector((1, 0, 0))
    t1 = normal.cross(helper).normalized()
    t2 = normal.cross(t1).normalized()
    angle = rng.uniform(0, math.tau)
    axis = (t1 * math.cos(angle) + t2 * math.sin(angle)).normalized()
    side = normal.cross(axis).normalized()
    rot = Matrix((side, normal, axis)).transposed().to_4x4()
    loc = Matrix.Translation(point + normal * RADIUS * 0.55)
    length = LENGTH * rng.uniform(0.8, 1.15)
    made = bmesh.ops.create_cone(bm, cap_ends=True, segments=8, radius1=RADIUS, radius2=RADIUS,
                                 depth=length, matrix=loc @ rot)
    index = rng.randrange(len(color_names))
    for face in {f for v in made["verts"] for f in v.link_faces}:
        face.material_index = index
        face.smooth = True

mesh = bpy.data.meshes.new("donut_sprinkles")
bm.to_mesh(mesh)
bm.free()
sprinkles = bpy.data.objects.new("donut_sprinkles", mesh)
asset.objects.link(sprinkles)
sub = sprinkles.modifiers.new("Subdivision", "SUBSURF")  # rounds the ends into little pills
sub.levels, sub.render_levels = 1, 1

for name in color_names:
    mat = bpy.data.materials.new("MAT_sprinkle_" + name)
    mat.use_nodes = True
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = COLORS[name]
    bsdf.inputs["Roughness"].default_value = 0.35
    mat.diffuse_color = COLORS[name]
    mesh.materials.append(mat)

bpy.context.scene["sprinkle_count"] = len(placed)
print(f"Sprinkles: {len(placed)} placed in {attempts} attempts")
