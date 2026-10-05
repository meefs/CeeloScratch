# Step 6 - write the deliverables into the versioned asset folder:
#   <name>.blend (source scene), <name>.glb (real-time copy), renders/<name>_hero.png, asset.json
import json
import os
import platform
import time

import bpy

out_dir = PARAMS["output_dir"]
name = PARAMS["file_stem"]
os.makedirs(os.path.join(out_dir, "renders"), exist_ok=True)
blend_path = os.path.join(out_dir, name + ".blend")
glb_path = os.path.join(out_dir, name + ".glb")
png_path = os.path.join(out_dir, "renders", name + "_hero.png")
scene = bpy.context.scene

# 1. Render the hero still.
t0 = time.time()
scene.render.filepath = png_path
bpy.ops.render.render(write_still=True)
render_seconds = time.time() - t0

# 2. Save the source .blend (compressed, relative paths) for future editing.
bpy.ops.wm.save_as_mainfile(filepath=blend_path, compress=True, relative_remap=True)

# 3. Export only the donut itself (not the stage) as glTF binary for games / web / AR.
asset = bpy.data.collections["ASSET_" + PARAMS["asset_name"]]
for obj in bpy.context.view_layer.objects:
    obj.select_set(obj.name in asset.objects)
bpy.ops.export_scene.gltf(filepath=glb_path, export_format="GLB", use_selection=True,
                          export_apply=True, export_yup=True)

# 4. Describe what was made, for humans and for later pipelines.
depsgraph = bpy.context.evaluated_depsgraph_get()
parts = {}
for obj in asset.objects:
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    parts[obj.name] = {"vertices": len(mesh.vertices), "faces": len(mesh.polygons),
                       "materials": [m.name for m in obj.data.materials]}
    evaluated.to_mesh_clear()

meta = {
    "asset": PARAMS["asset_name"],
    "version": PARAMS["version"],
    "description": "Pink-iced donut with rainbow sprinkles, real-world scale (~9 cm diameter), Z-up in .blend, Y-up in .glb.",
    "units": "meters",
    "seed": PARAMS["seed"],
    "sprinkle_count": int(scene.get("sprinkle_count", 0)),
    "parts": parts,
    "files": {
        "blend": os.path.basename(blend_path),
        "glb": os.path.basename(glb_path),
        "hero_render": "renders/" + os.path.basename(png_path),
    },
    "render": {
        "engine": scene.render.engine,
        "device": scene.cycles.device,
        "samples": scene.cycles.samples,
        "resolution": [scene.render.resolution_x, scene.render.resolution_y],
        "seconds": round(render_seconds, 1),
    },
    "built_with": {
        "blender": bpy.app.version_string,
        "machine": platform.machine(),
        "os": platform.platform(),
        "control": "MCP for Blender (execute_blender_code)",
    },
}
with open(os.path.join(out_dir, "asset.json"), "w") as fh:
    json.dump(meta, fh, indent=2)
    fh.write("\n")

print(json.dumps({"render_seconds": round(render_seconds, 1), "files": meta["files"]}))
