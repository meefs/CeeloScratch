# Step 2 - the baked dough: a slightly squashed, lumpy torus about 9 cm across.
import math

import bmesh
import bpy
from mathutils import Vector, noise

asset = bpy.data.collections["ASSET_" + PARAMS["asset_name"]]

# Build the torus by hand so the result does not depend on operator context.
major_r, minor_r = 0.032, 0.0145
major_seg, minor_seg = 64, 32
bm = bmesh.new()
rings = []
for i in range(major_seg):
    u = 2 * math.pi * i / major_seg
    ring = []
    for j in range(minor_seg):
        v = 2 * math.pi * j / minor_seg
        x = (major_r + minor_r * math.cos(v)) * math.cos(u)
        y = (major_r + minor_r * math.cos(v)) * math.sin(u)
        z = minor_r * math.sin(v) * 0.82  # squash: donuts rise less than they spread
        ring.append(bm.verts.new((x, y, z)))
    rings.append(ring)
for i in range(major_seg):
    for j in range(minor_seg):
        a = rings[i][j]
        b = rings[(i + 1) % major_seg][j]
        c = rings[(i + 1) % major_seg][(j + 1) % minor_seg]
        d = rings[i][(j + 1) % minor_seg]
        bm.faces.new((a, b, c, d))
bm.normal_update()

# Hand-made lumpiness: low-frequency noise pushed along the normals.
seed_offset = Vector((PARAMS["seed"] * 1.37, PARAMS["seed"] * 0.71, 0.0))
for vert in bm.verts:
    n = noise.noise(vert.co * 60.0 + seed_offset)
    vert.co += vert.normal * n * 0.0011

mesh = bpy.data.meshes.new("donut_body")
bm.to_mesh(mesh)
bm.free()
for poly in mesh.polygons:
    poly.use_smooth = True

body = bpy.data.objects.new("donut_body", mesh)
asset.objects.link(body)
sub = body.modifiers.new("Subdivision", "SUBSURF")
sub.levels, sub.render_levels = 1, 2

# Dough material: golden-brown with a pale "belt" around the equator, like a real fried donut.
mat = bpy.data.materials.new("MAT_dough")
mat.use_nodes = True
nodes, links = mat.node_tree.nodes, mat.node_tree.links
bsdf = next(n for n in nodes if n.type == "BSDF_PRINCIPLED")
bsdf.inputs["Roughness"].default_value = 0.6

geo = nodes.new("ShaderNodeNewGeometry")
sep = nodes.new("ShaderNodeSeparateXYZ")
absn = nodes.new("ShaderNodeMath"); absn.operation = "ABSOLUTE"
ramp = nodes.new("ShaderNodeValToRGB")
ramp.color_ramp.elements[0].position = 0.25
ramp.color_ramp.elements[0].color = (0.80, 0.52, 0.24, 1.0)  # lighter belt
ramp.color_ramp.elements[1].position = 0.6
ramp.color_ramp.elements[1].color = (0.36, 0.15, 0.04, 1.0)  # browned crust
tex = nodes.new("ShaderNodeTexNoise"); tex.inputs["Scale"].default_value = 400.0
bump = nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.15

links.new(geo.outputs["Normal"], sep.inputs["Vector"])
links.new(sep.outputs["Z"], absn.inputs[0])
links.new(absn.outputs["Value"], ramp.inputs["Fac"])
links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
links.new(tex.outputs["Fac"], bump.inputs["Height"])
links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
mat.diffuse_color = (0.75, 0.5, 0.28, 1.0)  # viewport / glTF fallback
body.data.materials.append(mat)

print(f"Donut body: {len(mesh.vertices)} verts")
