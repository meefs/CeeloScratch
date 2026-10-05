# Step 7 - turntable: spin the donut a full 360 degrees and render each frame for the README GIF.
# Runs after the .blend is saved, so the saved scene stays un-animated.
import json
import math
import os
import time

import bpy

tt = PARAMS["turntable"]
scene = bpy.context.scene
asset = bpy.data.collections["ASSET_" + PARAMS["asset_name"]]
frames_dir = tt["frames_dir"]
os.makedirs(frames_dir, exist_ok=True)

# Parent the donut parts to a pivot at the origin and rotate that, so the lights and camera stay put.
pivot = bpy.data.objects.new("turntable_pivot", None)
bpy.data.collections["STAGE"].objects.link(pivot)
for obj in asset.objects:
    obj.parent = pivot

scene.render.resolution_x = tt["width"]
scene.render.resolution_y = tt["height"]
scene.cycles.samples = tt["samples"]

t0 = time.time()
count = tt["frames"]
for i in range(count):
    pivot.rotation_euler.z = 2 * math.pi * i / count
    scene.render.filepath = os.path.join(frames_dir, f"frame_{i:03d}.png")
    bpy.ops.render.render(write_still=True)
seconds = time.time() - t0

meta_path = os.path.join(PARAMS["output_dir"], "asset.json")
with open(meta_path) as fh:
    meta = json.load(fh)
meta["turntable"] = {"frames": count, "resolution": [tt["width"], tt["height"]],
                     "samples": tt["samples"], "fps": tt["fps"], "seconds": round(seconds, 1)}
with open(meta_path, "w") as fh:
    json.dump(meta, fh, indent=2)
    fh.write("\n")

print(f"Turntable: {count} frames in {seconds:.1f}s ({seconds / count:.1f}s per frame)")
