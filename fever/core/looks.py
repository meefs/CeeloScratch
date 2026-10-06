"""Material recipes for the fever dreams: tints, iridescence, glowing images, HDRI portals, butterfly wings.

Per-instance variation uses cheap per-object data so thousands of copies can share one material:
``Object Info > Color`` (obj.color, animated from Python each frame), ``Object Info > Alpha`` and
``Object Info > Random``, or object custom properties read with an Attribute node.
"""

import colorsys

import bpy


def hsv(h, s=1.0, v=1.0, a=1.0):
    return (*colorsys.hsv_to_rgb(h % 1.0, s, v), a)


def _new(name):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
    return mat, nt, bsdf, out


def _set(node, name, value):
    if name in node.inputs:
        node.inputs[name].default_value = value


def principled(name, color, roughness=0.5, metallic=0.0, coat=0.0, emission=None, strength=0.0,
               transmission=0.0, sheen=0.0, thin_film=0.0):
    mat, nt, bsdf, _ = _new(name)
    _set(bsdf, "Base Color", color if len(color) == 4 else (*color, 1))
    _set(bsdf, "Roughness", roughness)
    _set(bsdf, "Metallic", metallic)
    _set(bsdf, "Coat Weight", coat)
    _set(bsdf, "Transmission Weight", transmission)
    _set(bsdf, "Sheen Weight", sheen)
    if thin_film:
        _set(bsdf, "Thin Film Thickness", thin_film)  # Blender 4.2+
    if emission is not None:
        _set(bsdf, "Emission Color", emission if len(emission) == 4 else (*emission, 1))
        _set(bsdf, "Emission Strength", strength)
    mat.diffuse_color = color if len(color) == 4 else (*color, 1)
    return mat


def object_color(name, roughness=0.35, metallic=0.0, coat=0.3, sheen=0.0, glow=0.0):
    """Principled material whose base (and optional glow) colour comes from each object's obj.color."""
    mat, nt, bsdf, _ = _new(name)
    info = nt.nodes.new("ShaderNodeObjectInfo")
    nt.links.new(info.outputs["Color"], bsdf.inputs["Base Color"])
    _set(bsdf, "Roughness", roughness)
    _set(bsdf, "Metallic", metallic)
    _set(bsdf, "Coat Weight", coat)
    _set(bsdf, "Sheen Weight", sheen)
    if glow:
        nt.links.new(info.outputs["Color"], bsdf.inputs["Emission Color"])
        _set(bsdf, "Emission Strength", glow)
    return mat


def tint_with_object_color(mat, amount=1.0):
    """Multiply an existing (e.g. Poly Haven) material's base colour by each object's obj.color."""
    if not mat or not mat.use_nodes:
        return
    nt = mat.node_tree
    for bsdf in [n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"]:
        base = bsdf.inputs["Base Color"]
        info = nt.nodes.new("ShaderNodeObjectInfo")
        mix = nt.nodes.new("ShaderNodeMixRGB")
        mix.blend_type = "MULTIPLY"
        mix.inputs["Fac"].default_value = amount
        if base.is_linked:
            nt.links.new(base.links[0].from_socket, mix.inputs["Color1"])
        else:
            mix.inputs["Color1"].default_value = base.default_value
        nt.links.new(info.outputs["Color"], mix.inputs["Color2"])
        nt.links.new(mix.outputs["Color"], base)


def iridescent(name, roughness=0.12, glow=0.15):
    """Oil-slick rainbow: hue follows the viewing angle, plus thin-film interference where supported."""
    mat, nt, bsdf, _ = _new(name)
    lw = nt.nodes.new("ShaderNodeLayerWeight")
    lw.inputs["Blend"].default_value = 0.35
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    els = ramp.color_ramp.elements
    els[0].color, els[1].color = hsv(0.0), hsv(0.83)
    for i, pos in enumerate((0.17, 0.33, 0.5, 0.66)):
        e = els.new(pos)
        e.color = hsv((i + 1) / 6)
    nt.links.new(lw.outputs["Facing"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Emission Color"])
    _set(bsdf, "Emission Strength", glow)
    _set(bsdf, "Metallic", 0.85)
    _set(bsdf, "Roughness", roughness)
    _set(bsdf, "Thin Film Thickness", 420.0)
    return mat


def glowing_image(name, image_path, strength=1.6):
    """Emissive, translucent picture plane: RGB x obj.color, opacity = image alpha x obj.color alpha.

    Returns (material, hue_node) so the caller can rotate the hue every frame.
    """
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(str(image_path), check_existing=True)
    tex.interpolation = "Linear"
    info = nt.nodes.new("ShaderNodeObjectInfo")
    hue = nt.nodes.new("ShaderNodeHueSaturation")
    tint = nt.nodes.new("ShaderNodeMixRGB")
    tint.blend_type = "MULTIPLY"
    tint.inputs["Fac"].default_value = 1.0
    emit = nt.nodes.new("ShaderNodeEmission")
    emit.inputs["Strength"].default_value = strength
    clear = nt.nodes.new("ShaderNodeBsdfTransparent")
    mix = nt.nodes.new("ShaderNodeMixShader")
    alpha = nt.nodes.new("ShaderNodeMath")
    alpha.operation = "MULTIPLY"
    nt.links.new(tex.outputs["Color"], hue.inputs["Color"])
    nt.links.new(hue.outputs["Color"], tint.inputs["Color1"])
    nt.links.new(info.outputs["Color"], tint.inputs["Color2"])
    nt.links.new(tint.outputs["Color"], emit.inputs["Color"])
    nt.links.new(tex.outputs["Alpha"], alpha.inputs[0])
    nt.links.new(info.outputs["Alpha"], alpha.inputs[1])
    nt.links.new(alpha.outputs["Value"], mix.inputs["Fac"])
    nt.links.new(clear.outputs["BSDF"], mix.inputs[1])
    nt.links.new(emit.outputs["Emission"], mix.inputs[2])
    nt.links.new(mix.outputs["Shader"], out.inputs["Surface"])
    return mat, hue


def hdri_portal(name, hdri_path, rim=(0.02, 0.02, 0.03)):
    """A sphere that shows another Poly Haven world: the HDRI looked up along the reflection vector.

    Returns (material, mapping_node) so the world inside can be spun each frame.
    """
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    coord = nt.nodes.new("ShaderNodeTexCoord")
    mapping = nt.nodes.new("ShaderNodeMapping")
    env = nt.nodes.new("ShaderNodeTexEnvironment")
    env.image = bpy.data.images.load(str(hdri_path), check_existing=True)
    emit = nt.nodes.new("ShaderNodeEmission")
    emit.inputs["Strength"].default_value = 1.0
    glossy = nt.nodes.new("ShaderNodeBsdfGlossy")
    glossy.inputs["Color"].default_value = (*rim, 1)
    glossy.inputs["Roughness"].default_value = 0.05
    fres = nt.nodes.new("ShaderNodeFresnel")
    fres.inputs["IOR"].default_value = 1.6
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(coord.outputs["Reflection"], mapping.inputs["Vector"])
    nt.links.new(mapping.outputs["Vector"], env.inputs["Vector"])
    nt.links.new(env.outputs["Color"], emit.inputs["Color"])
    nt.links.new(fres.outputs["Fac"], mix.inputs["Fac"])
    nt.links.new(emit.outputs["Emission"], mix.inputs[1])
    nt.links.new(glossy.outputs["BSDF"], mix.inputs[2])
    nt.links.new(mix.outputs["Shader"], out.inputs["Surface"])
    return mat, mapping


def butterfly_wing(name):
    """One shared wing material; every butterfly looks unique via its 'wing_seed' custom property.

    The seed drives hue, eye-spot placement, vein frequency and a 4D Voronoi pattern; both wings of a
    butterfly carry the same seed so they match.
    """
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    L, N = nt.links.new, nt.nodes.new
    out = N("ShaderNodeOutputMaterial")
    seed = N("ShaderNodeAttribute")
    seed.attribute_type = "OBJECT"
    seed.attribute_name = "wing_seed"
    uv = N("ShaderNodeTexCoord")
    # Hue pair from the seed.
    hue_b = N("ShaderNodeMath"); hue_b.operation = "ADD"; hue_b.inputs[1].default_value = 0.45
    col_a = N("ShaderNodeCombineColor"); col_a.mode = "HSV"
    col_b = N("ShaderNodeCombineColor"); col_b.mode = "HSV"
    for c, s in ((col_a, 0.95), (col_b, 0.85)):
        c.inputs[1].default_value = s
        c.inputs[2].default_value = 1.0
    L(seed.outputs["Fac"], col_a.inputs[0])
    L(seed.outputs["Fac"], hue_b.inputs[0])
    L(hue_b.outputs["Value"], col_b.inputs[0])
    # Pattern: 4D Voronoi (w = seed) + wavy veins + an eye-spot ring.
    vor = N("ShaderNodeTexVoronoi"); vor.voronoi_dimensions = "4D"; vor.inputs["Scale"].default_value = 7.0
    w = N("ShaderNodeMath"); w.operation = "MULTIPLY"; w.inputs[1].default_value = 97.0
    L(seed.outputs["Fac"], w.inputs[0])
    L(w.outputs["Value"], vor.inputs["W"])
    L(uv.outputs["UV"], vor.inputs["Vector"])
    wave = N("ShaderNodeTexWave"); wave.wave_type = "RINGS"; wave.inputs["Scale"].default_value = 3.0
    wave.inputs["Distortion"].default_value = 4.0
    L(uv.outputs["UV"], wave.inputs["Vector"])
    pattern = N("ShaderNodeMath"); pattern.operation = "MULTIPLY"
    L(vor.outputs["Distance"], pattern.inputs[0])
    L(wave.outputs["Fac"], pattern.inputs[1])
    ramp = N("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.15
    ramp.color_ramp.elements[1].position = 0.55
    L(pattern.outputs["Value"], ramp.inputs["Fac"])
    mix = N("ShaderNodeMixRGB")
    L(ramp.outputs["Color"], mix.inputs["Fac"])
    L(col_a.outputs["Color"], mix.inputs["Color1"])
    L(col_b.outputs["Color"], mix.inputs["Color2"])
    # Dark wing margin.
    sep = N("ShaderNodeSeparateXYZ")
    L(uv.outputs["UV"], sep.inputs[0])
    edge = N("ShaderNodeMath"); edge.operation = "GREATER_THAN"; edge.inputs[1].default_value = 0.86
    L(sep.outputs["X"], edge.inputs[0])
    margin = N("ShaderNodeMixRGB"); margin.inputs["Color2"].default_value = (0.01, 0.01, 0.015, 1)
    L(edge.outputs["Value"], margin.inputs["Fac"])
    L(mix.outputs["Color"], margin.inputs["Color1"])
    bsdf = N("ShaderNodeBsdfPrincipled")
    _set(bsdf, "Roughness", 0.45)
    _set(bsdf, "Sheen Weight", 0.6)
    _set(bsdf, "Emission Strength", 0.9)
    L(margin.outputs["Color"], bsdf.inputs["Base Color"])
    L(margin.outputs["Color"], bsdf.inputs["Emission Color"])
    trans = N("ShaderNodeBsdfTranslucent")
    L(margin.outputs["Color"], trans.inputs["Color"])
    both = N("ShaderNodeMixShader"); both.inputs["Fac"].default_value = 0.3
    L(bsdf.outputs["BSDF"], both.inputs[1])
    L(trans.outputs["BSDF"], both.inputs[2])
    L(both.outputs["Shader"], out.inputs["Surface"])
    return mat


def flat_emissive(mat_or_color, name, strength=1.0, facing_shade=0.45):
    """Self-lit 'toon' version of a colour or a Poly Haven material's diffuse map, tinted by obj.color.

    Used where lighting must be identical at every scale (the infinite TV zoom), so nothing depends on lights.
    """
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    emit = nt.nodes.new("ShaderNodeEmission")
    emit.inputs["Strength"].default_value = strength
    info = nt.nodes.new("ShaderNodeObjectInfo")
    tint = nt.nodes.new("ShaderNodeMixRGB"); tint.blend_type = "MULTIPLY"; tint.inputs["Fac"].default_value = 1.0
    lw = nt.nodes.new("ShaderNodeLayerWeight"); lw.inputs["Blend"].default_value = 0.5
    rim = nt.nodes.new("ShaderNodeInvert")  # 1 facing the camera, falling to 0 at grazing angles
    shade = nt.nodes.new("ShaderNodeMixRGB"); shade.blend_type = "MULTIPLY"
    shade.inputs["Fac"].default_value = facing_shade
    src_color = None
    if isinstance(mat_or_color, bpy.types.Material) and mat_or_color.use_nodes:
        img = next((n for n in mat_or_color.node_tree.nodes if n.type == "TEX_IMAGE" and n.image
                    and "diff" in n.image.name.lower()), None) or \
              next((n for n in mat_or_color.node_tree.nodes if n.type == "TEX_IMAGE" and n.image), None)
        if img:
            tex = nt.nodes.new("ShaderNodeTexImage")
            tex.image = img.image
            src_color = tex.outputs["Color"]
    if src_color is None:
        color = mat_or_color if isinstance(mat_or_color, tuple) else (0.6, 0.6, 0.6)
        tint.inputs["Color1"].default_value = color if len(color) == 4 else (*color, 1)
    else:
        nt.links.new(src_color, tint.inputs["Color1"])
    nt.links.new(info.outputs["Color"], tint.inputs["Color2"])
    nt.links.new(tint.outputs["Color"], shade.inputs["Color1"])
    nt.links.new(lw.outputs["Facing"], rim.inputs["Color"])
    nt.links.new(rim.outputs["Color"], shade.inputs["Color2"])
    nt.links.new(shade.outputs["Color"], emit.inputs["Color"])
    nt.links.new(emit.outputs["Emission"], out.inputs["Surface"])
    return mat
