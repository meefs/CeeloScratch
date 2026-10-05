# Step 5 - a simple product-shot stage: seamless backdrop, three-point lighting, camera, render settings.
import math

import bmesh
import bpy
from mathutils import Vector

scene = bpy.context.scene
stage = bpy.data.collections["STAGE"]

# Seamless "cyclorama" backdrop: a floor that curves up into a back wall.
bm = bmesh.new()
profile = []
for i in range(25):
    t = i / 24
    if t < 0.5:
        profile.append((-0.25 + t * 2 * 0.35, 0.0))          # floor, y from -0.25 to 0.10
    else:
        a = (t - 0.5) * 2 * (math.pi / 2)
        profile.append((0.10 + math.sin(a) * 0.15, 0.15 - math.cos(a) * 0.15))  # curve up the wall
rows = [[bm.verts.new((x, y, z)) for x in (-0.4, 0.4)] for y, z in profile]
for r0, r1 in zip(rows, rows[1:]):
    bm.faces.new((r0[0], r0[1], r1[1], r1[0]))
bm.normal_update()
mesh = bpy.data.meshes.new("backdrop")
bm.to_mesh(mesh)
bm.free()
for poly in mesh.polygons:
    poly.use_smooth = True
backdrop = bpy.data.objects.new("backdrop", mesh)
backdrop.location.z = -0.0125  # rest the donut on the floor
stage.objects.link(backdrop)
mat = bpy.data.materials.new("MAT_backdrop")
mat.use_nodes = True
bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
bsdf.inputs["Base Color"].default_value = (0.86, 0.93, 0.95, 1.0)  # pale sky, lets the pink pop
bsdf.inputs["Roughness"].default_value = 0.8
backdrop.data.materials.append(mat)


def area_light(name, location, energy, size, color=(1.0, 1.0, 1.0)):
    light = bpy.data.lights.new(name, "AREA")
    light.energy, light.size, light.color = energy, size, color
    obj = bpy.data.objects.new(name, light)
    obj.location = location
    direction = Vector((0, 0, 0)) - Vector(location)
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    stage.objects.link(obj)
    return obj


area_light("key_light", (0.18, -0.14, 0.22), 1.1, 0.18, (1.0, 0.96, 0.92))
area_light("fill_light", (-0.22, -0.10, 0.10), 0.3, 0.25, (0.90, 0.95, 1.0))
area_light("rim_light", (-0.05, 0.22, 0.16), 0.8, 0.12)

world = bpy.data.worlds.get("World") or bpy.data.worlds.new("World")
scene.world = world
world.use_nodes = True
bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
bg.inputs["Color"].default_value = (0.80, 0.86, 0.92, 1.0)
bg.inputs["Strength"].default_value = 0.12

# Camera: 3/4 view from above, slight depth of field focused on the front of the donut.
cam_data = bpy.data.cameras.new("hero_camera")
cam_data.lens = 70
cam_data.dof.use_dof = True
cam_data.dof.aperture_fstop = 5.6
cam = bpy.data.objects.new("hero_camera", cam_data)
cam.location = (0.0, -0.21, 0.17)
target = Vector((0.0, 0.0, -0.002))
cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
cam_data.dof.focus_distance = (target - cam.location).length - 0.01
stage.objects.link(cam)
scene.camera = cam

# Render settings: Cycles on CPU (CI runners have no usable GPU).
render = PARAMS["render"]
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = render["samples"]
scene.cycles.use_adaptive_sampling = True
scene.cycles.adaptive_threshold = 0.02
scene.cycles.use_denoising = True
scene.cycles.max_bounces = 8
scene.render.resolution_x = render["width"]
scene.render.resolution_y = render["height"]
scene.render.resolution_percentage = 100
scene.render.film_transparent = False
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGB"
try:
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Punchy"
except TypeError:
    pass  # older colour management names; defaults are fine

print(f"Stage ready: {render['width']}x{render['height']} @ {render['samples']} spp")
