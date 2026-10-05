# Luscious pass: wetter icing, glossier sprinkles, warmer glamour lighting, shallower focus.
import math
import bpy
from mathutils import Vector

scene = bpy.context.scene

def bsdf_of(name):
    mat = bpy.data.materials[name]
    return next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")

icing = bsdf_of("MAT_icing_pink")
icing.inputs["Base Color"].default_value = (0.97, 0.10, 0.38, 1.0)
icing.inputs["Roughness"].default_value = 0.08
for name, value in (("Coat Weight", 0.8), ("Coat Roughness", 0.03), ("Subsurface Weight", 0.25),
                    ("Subsurface Radius", None), ("Specular IOR Level", 0.6)):
    if name in icing.inputs and value is not None:
        icing.inputs[name].default_value = value

for mat in bpy.data.materials:
    if mat.name.startswith("MAT_sprinkle_"):
        b = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        b.inputs["Roughness"].default_value = 0.18
        if "Coat Weight" in b.inputs:
            b.inputs["Coat Weight"].default_value = 0.5

dough = bsdf_of("MAT_dough")
if "Sheen Weight" in dough.inputs:  # soft sugary fuzz on the fried dough
    dough.inputs["Sheen Weight"].default_value = 0.4

# Glamour lighting: big warm key, cool fill, hot rim for glistening edges, soft top light.
lights = {o.name: o for o in bpy.data.objects if o.type == "LIGHT"}
lights["key_light"].data.energy = 1.4
lights["key_light"].data.size = 0.30
lights["key_light"].data.color = (1.0, 0.90, 0.82)
lights["fill_light"].data.energy = 0.35
lights["fill_light"].data.color = (0.85, 0.90, 1.0)
lights["rim_light"].data.energy = 2.2
lights["rim_light"].data.size = 0.06
top = bpy.data.lights.new("top_softbox", "AREA")
top.energy, top.size, top.color = 0.6, 0.35, (1.0, 0.95, 0.97)
top_obj = bpy.data.objects.new("top_softbox", top)
top_obj.location = (0.0, 0.0, 0.30)
bpy.data.collections["STAGE"].objects.link(top_obj)

# Backdrop: blush pink so the whole frame feels candy-sweet.
bd = bsdf_of("MAT_backdrop")
bd.inputs["Base Color"].default_value = (0.95, 0.80, 0.84, 1.0)

# Camera: lower, closer, dreamy shallow focus.
cam = scene.camera
cam.data.lens = 85
cam.data.dof.aperture_fstop = 4.0
cam["base_location"] = (0.0, -0.26, 0.16)
cam.location = cam["base_location"]
cam.rotation_euler = (Vector((0.0, 0.0, 0.0)) - cam.location).to_track_quat("-Z", "Y").to_euler()
cam.data.dof.focus_distance = cam.location.length - 0.012
print("Luscious pass applied")
