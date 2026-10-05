# Step 3 - glossy pink icing: the top of the donut, with a wavy drippy edge, given thickness.
import bmesh
import bpy
from mathutils import Vector, noise

asset = bpy.data.collections["ASSET_" + PARAMS["asset_name"]]
body = bpy.data.objects["donut_body"]

bm = bmesh.new()
bm.from_mesh(body.data)
bm.normal_update()

# Keep the faces above a wobbly "waterline"; the noise makes the icing edge drip unevenly.
seed_offset = Vector((PARAMS["seed"] * 2.11, 0.0, PARAMS["seed"] * 0.53))
doomed = []
for face in bm.faces:
    c = face.calc_center_median()
    waterline = 0.0025 + noise.noise(c * 90.0 + seed_offset) * 0.0035
    if c.z < waterline:
        doomed.append(face)
bmesh.ops.delete(bm, geom=doomed, context="FACES")

# Float the icing just off the dough so the two surfaces never z-fight.
for vert in bm.verts:
    vert.co += vert.normal * 0.0004

mesh = bpy.data.meshes.new("donut_icing")
bm.to_mesh(mesh)
bm.free()
for poly in mesh.polygons:
    poly.use_smooth = True

icing = bpy.data.objects.new("donut_icing", mesh)
asset.objects.link(icing)
solid = icing.modifiers.new("Solidify", "SOLIDIFY")
solid.thickness = 0.0016
solid.offset = 1.0
solid.use_rim = True
sub = icing.modifiers.new("Subdivision", "SUBSURF")
sub.levels, sub.render_levels = 1, 2

mat = bpy.data.materials.new("MAT_icing_pink")
mat.use_nodes = True
bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
pink = (0.95, 0.12, 0.40, 1.0)
bsdf.inputs["Base Color"].default_value = pink
bsdf.inputs["Roughness"].default_value = 0.22
for name, value in (("Subsurface Weight", 0.15), ("Coat Weight", 0.35)):
    if name in bsdf.inputs:  # Blender 4.x Principled v2 names
        bsdf.inputs[name].default_value = value
mat.diffuse_color = pink
icing.data.materials.append(mat)

print(f"Icing: {len(mesh.polygons)} faces kept")
