"""Renderer setup (through BlenderProc + Cycles) and the per-frame render loop."""

import time
from pathlib import Path

import blenderproc as bproc
import bpy

from fever.core.loop import QUALITY


def configure(ctx, transparent_bounces=32, glossy_bounces=4):
    scene = bpy.context.scene
    bproc.camera.set_resolution(ctx.width, ctx.height)
    bproc.renderer.set_max_amount_of_samples(ctx.samples)
    bproc.renderer.set_noise_threshold(0.03)
    bproc.renderer.set_light_bounces(diffuse_bounces=3, glossy_bounces=glossy_bounces, max_bounces=8,
                                     transmission_bounces=6, transparent_max_bounces=transparent_bounces,
                                     volume_bounces=0)
    scene.render.engine = "CYCLES"
    cycles = scene.cycles
    cycles.device = "CPU"  # GitHub-hosted runners have no GPU
    cycles.use_denoising = True
    try:
        cycles.denoiser = "OPENIMAGEDENOISE"
    except TypeError:
        pass
    cycles.caustics_reflective = False
    cycles.caustics_refractive = False
    cycles.blur_glossy = 0.6
    scene.render.use_persistent_data = True  # keep BVH/images between frames when only transforms change
    scene.render.use_compositing = False
    scene.render.use_sequencer = False
    scene.render.film_transparent = False
    settings = scene.render.image_settings
    settings.file_format = "PNG"
    settings.color_mode = "RGB"
    settings.color_depth = "8"
    try:
        scene.view_settings.view_transform = "AgX"
        scene.view_settings.look = "AgX - Punchy"
    except TypeError:
        pass
    scene.render.fps = ctx.fps
    scene.frame_start, scene.frame_end = 0, ctx.n_frames - 1


def frames_for(ctx, shard, shards):
    """This shard's frames: a contiguous slice of the loop, or a few spread-out frames for previews."""
    if ctx.quality == "preview":
        k = QUALITY["preview"]["preview_frames"]
        frames = sorted({round(i * ctx.n_frames / k) for i in range(k)})
    else:
        frames = list(range(ctx.n_frames))
    lo, hi = len(frames) * shard // shards, len(frames) * (shard + 1) // shards
    return frames[lo:hi]


def render_frames(ctx, update, frames, out_dir):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    seconds = {}
    for f in frames:
        t0 = time.time()
        scene.frame_set(f)
        update(f)
        scene.render.filepath = str(out_dir / f"frame_{f:04d}.png")
        bpy.ops.render.render(write_still=True)
        seconds[f] = round(time.time() - t0, 2)
        print(f"[fever] {ctx.id} frame {f + 1}/{ctx.n_frames} in {seconds[f]}s", flush=True)
    return seconds
