# Step 1 - start from an empty, metric scene.
# Runs inside Blender via the MCP `execute_blender_code` tool; PARAMS is injected by the driver.
import bpy

for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)
for collection in (bpy.data.meshes, bpy.data.materials, bpy.data.cameras,
                   bpy.data.lights, bpy.data.images, bpy.data.textures):
    for block in list(collection):
        collection.remove(block)

scene = bpy.context.scene
scene.name = PARAMS["asset_name"]
scene.unit_settings.system = "METRIC"
scene.unit_settings.scale_length = 1.0  # real-world scale: 1 unit = 1 m
scene.frame_start = scene.frame_end = scene.frame_current = 1

asset = bpy.data.collections.new("ASSET_" + PARAMS["asset_name"])
stage = bpy.data.collections.new("STAGE")
scene.collection.children.link(asset)
scene.collection.children.link(stage)

print(f"Scene reset; Blender {bpy.app.version_string}")
