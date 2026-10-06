"""Poly Haven assets through BlenderProc: HDRI worlds, PBR textures and models, with procedural fallbacks.

The assets were fetched on the runner by ``blenderproc download haven`` (see fever/tools/fetch_haven.sh)
and narrowed per scene by fever/tools/select_assets.py; here they are loaded with BlenderProc's own
loaders: ``bproc.world.set_world_background_hdr_img``, ``bproc.loader.load_haven_mat`` and
``bproc.loader.load_blend``.
"""

import blenderproc as bproc
import bpy
import numpy as np

from fever.core import looks


class World:
    """World lighting: a Poly Haven HDRI (or a gradient fallback) with an animatable hue rotation."""

    def __init__(self, ctx, role="world", strength=1.0, fallback=((0.05, 0.02, 0.10), (0.6, 0.3, 0.8))):
        world = bpy.context.scene.world
        path = ctx.hdri(role)
        if path:
            bproc.world.set_world_background_hdr_img(str(path), strength=strength)
            world = bpy.context.scene.world
            nt = world.node_tree
            env = next(n for n in nt.nodes if n.type == "TEX_ENVIRONMENT")
            bg = next(n for n in nt.nodes if n.type == "BACKGROUND")
            self.mapping = next((n for n in nt.nodes if n.type == "MAPPING"), None)
        else:
            world.use_nodes = True
            nt = world.node_tree
            nt.nodes.clear()
            out = nt.nodes.new("ShaderNodeOutputWorld")
            bg = nt.nodes.new("ShaderNodeBackground")
            bg.inputs["Strength"].default_value = strength
            coord = nt.nodes.new("ShaderNodeTexCoord")
            sep = nt.nodes.new("ShaderNodeSeparateXYZ")
            env = nt.nodes.new("ShaderNodeValToRGB")
            env.color_ramp.elements[0].color = (*fallback[0], 1)
            env.color_ramp.elements[1].color = (*fallback[1], 1)
            nt.links.new(coord.outputs["Generated"], sep.inputs[0])
            nt.links.new(sep.outputs["Z"], env.inputs["Fac"])
            nt.links.new(bg.outputs["Background"], out.inputs["Surface"])
            self.mapping = None
        # Insert a hue rotation between the environment colour and the background shader.
        hue = nt.nodes.new("ShaderNodeHueSaturation")
        nt.links.new(env.outputs["Color"], hue.inputs["Color"])
        nt.links.new(hue.outputs["Color"], bg.inputs["Color"])
        self.hue = hue
        self.background = bg

    def set(self, hue_shift=0.0, saturation=1.0, strength=None, rotation_z=None):
        self.hue.inputs["Hue"].default_value = (0.5 + hue_shift) % 1.0
        self.hue.inputs["Saturation"].default_value = saturation
        if strength is not None:
            self.background.inputs["Strength"].default_value = strength
        if rotation_z is not None and self.mapping is not None:
            self.mapping.inputs["Rotation"].default_value[2] = rotation_z


def texture_material(ctx, role, fallback_color=(0.5, 0.5, 0.5), roughness=0.6):
    """A Poly Haven PBR material loaded by BlenderProc, or a plain principled fallback."""
    folder = ctx.texture(role)
    if folder:
        mats = bproc.loader.load_haven_mat(folder_path=str(folder.parent), used_assets=[folder.name])
        mats = mats if isinstance(mats, list) else [mats]
        mat = next((m for m in mats if m.get_name() == folder.name), mats[0])
        return mat.blender_obj
    return looks.principled(f"MAT_{role}_fallback", fallback_color, roughness=roughness)


def load_model(ctx, role, height, collection=None):
    """Load a Poly Haven .blend model with BlenderProc, join it into one object, sit it on z=0, scale to height.

    Returns None when no model was selected, so the caller can build a procedural stand-in.
    """
    path = ctx.model(role)
    if not path:
        return None
    entities = bproc.loader.load_blend(str(path), obj_types=["mesh"])
    objs = [e.blender_obj for e in entities if e.blender_obj.type == "MESH"]
    if not objs:
        return None
    for o in objs:  # bake each part's world transform into its mesh, then drop parenting
        o.data = o.data.copy()
        o.data.transform(o.matrix_world)
        o.parent = None
        o.matrix_world.identity()
    if len(objs) > 1:
        with bpy.context.temp_override(active_object=objs[0], selected_editable_objects=objs,
                                       selected_objects=objs, object=objs[0]):
            bpy.ops.object.join()
    obj = objs[0]
    obj.name = f"SRC_{role}"
    normalize(obj, height)
    if collection is not None:
        for c in list(obj.users_collection):
            c.objects.unlink(obj)
        collection.objects.link(obj)
    return obj


def normalize(obj, height):
    """Centre the mesh on x/y, rest it on z=0 and scale it to the given height (in place, on the mesh)."""
    n = len(obj.data.vertices)
    co = np.empty(n * 3)
    obj.data.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    lo, hi = co.min(0), co.max(0)
    scale = height / max(hi[2] - lo[2], 1e-6)
    co = (co - np.array([(lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, lo[2]])) * scale
    obj.data.vertices.foreach_set("co", co.ravel())
    obj.data.update()
    return (hi - lo) * scale
