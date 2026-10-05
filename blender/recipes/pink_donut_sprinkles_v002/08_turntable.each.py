# Step 8 - slow turntable, one batch of frames per MCP call (PARAMS["batch"] lists this call's frames).
# The donut turns once over PARAMS["turntable"]["frames"]; the camera breathes gently on a loop.
import math
import os

import bpy
from mathutils import Vector

tt = PARAMS["turntable"]
scene = bpy.context.scene
asset = bpy.data.collections["ASSET_" + PARAMS["asset_name"]]

# First batch only: parent the donut to a pivot so the lights and camera stay put.
pivot = bpy.data.objects.get("turntable_pivot")
if pivot is None:
    pivot = bpy.data.objects.new("turntable_pivot", None)
    bpy.data.collections["STAGE"].objects.link(pivot)
    for obj in asset.objects:
        obj.parent = pivot

scene.render.resolution_x, scene.render.resolution_y = tt["width"], tt["height"]
scene.cycles.samples = tt["samples"]
scene.cycles.adaptive_threshold = 0.01
os.makedirs(tt["frames_dir"], exist_ok=True)

cam = scene.camera
base = Vector(cam["base_location"])
target = Vector((0.0, 0.0, 0.0))
count = tt["frames"]
for i in PARAMS["batch"]:
    phase = 2 * math.pi * i / count
    pivot.rotation_euler.z = phase
    # Rises and eases in/out twice per turn; periodic, so the loop is seamless.
    cam.location = base + Vector((0.0, 0.006 * math.sin(2 * phase), 0.008 * math.sin(phase)))
    cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
    cam.data.dof.focus_distance = (target - cam.location).length - 0.012
    scene.render.filepath = os.path.join(tt["frames_dir"], f"frame_{i:03d}.png")
    bpy.ops.render.render(write_still=True)
print(f"rendered frames {PARAMS['batch'][0]}-{PARAMS['batch'][-1]}")
