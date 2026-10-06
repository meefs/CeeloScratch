---
name: fever-dream-scene
description: Create, preview and publish a new "Fever Dream" in this repo - a seamless, headless, psychedelic Blender loop built with BlenderProc and Poly Haven assets and rendered in shards on GitHub Actions (fever/ + .github/workflows/fever-dreams.yml). Use when asked for a new surreal/avant-garde/procedural animation, to change an existing fever scene, to add Poly Haven assets to one, or to run, debug or publish the Fever Dreams workflow.
---

# Fever Dream scenes

Each Fever Dream is one Python module in `fever/scenes/`. GitHub runners render it headless with
BlenderProc (which brings its own Blender 4.2 LTS) and Cycles on CPU, in parallel shards, then stitch
the frames into a seamless MP4 plus a README preview WebP. **Never render on the session's own VM**:
the user wants all rendering on GitHub Actions. Local work is limited to editing code and cheap
static checks (`python -m py_compile`, `python fever/tools/plan.py`).

## Layout

| Path | Role |
|---|---|
| `fever/run_scene.py` | BlenderProc entry point: `blenderproc run fever/run_scene.py --scene ID --shard i --shards n --quality q --assets DIR --out DIR` |
| `fever/core/loop.py` | `Ctx`: loop timing, quality presets (`preview`/`standard`/`high`), the scene's chosen Poly Haven assets |
| `fever/core/assets.py` | Poly Haven through BlenderProc: `World` (HDRI + animatable hue), `texture_material`, `load_model` |
| `fever/core/looks.py` | Materials: `object_color`, `tint_with_object_color`, `iridescent`, `glowing_image`, `hdri_portal`, `butterfly_wing`, `flat_emissive` |
| `fever/core/geo.py` | `look_at`/`set_camera`/`camera_basis`, `basis`, `orthonormal`, closed-curve frames, torus knots, Lorenz, meshes from numpy, `link_copy` |
| `fever/core/props.py` | Procedural props: lawn chair, cowboy hat, butterfly, CRT TV, bust, hairy tribble, sphere |
| `fever/tools/` | Runner-side: `plan.py` (matrix), `fetch_haven.sh` (`blenderproc download haven`), `select_assets.py`, `decompose_gif.py`, `assemble.py`, `warmup.py` |
| `.github/workflows/fever-dreams.yml` | plan → setup (cached Blender + Poly Haven) → render (≤20 parallel) → assemble → publish |
| `assets/fever/<id>/` | Published `<id>.mp4`, `<id>_preview.webp`, `<id>_poster.png`, `scene.json` (README gallery reads these) |

## The scene contract

```python
SCENE = {                      # a pure literal: plan.py and select_assets.py read it with ast, no Blender
    "id": "my_scene",          # must equal the module name
    "title": "My Scene",
    "logline": "One sentence for the README.",
    "seconds": 16, "fps": 24,  # 10-30 s loops; frames = seconds * fps
    "shards": 8,               # runners for standard/high; ~30-50 frames per shard is a good size
    "aspect": "16:9",          # optional: "4:3", "1:1"
    "render": {"transparent_bounces": 128, "glossy_bounces": 10},   # optional overrides
    "haven": {                 # optional Poly Haven wishes: role -> keywords, most wanted first
        "hdris": {"world": ["night", "studio"]},
        "textures": {"floor": ["parquet", "carpet"]},
        "models": {"chair": ["monobloc", "chair"]},
        "hdri_pool": 24,       # optional: N distinct HDRIs (ctx.hdri_pool())
    },
}

def build(ctx):                # once per shard: create everything, return a state dict
    ...

def frame(ctx, state, t, f):   # pose everything for loop time t in [0, 1); f is the frame index
    ...
```

### Rules that keep loops seamless and shards consistent

1. **`frame()` is a pure function of `t`.** Never accumulate state from earlier frames; shards start
   mid-loop and frames render in any order. Rebuild per-frame geometry inside `frame()` if it changes
   (see `hairy_julia.py`), and reuse objects created in `build()` (create nothing per frame except replaced mesh data).
2. **Whole-number frequencies only.** Anything periodic is `sin(2*pi*(k*t + phase))` with integer `k`;
   camera orbits make whole laps; hue shifts move by whole turns. Then `t = 1` equals `t = 0`.
3. **Treadmills and zooms close exactly.** Scroll textures by whole tiles per loop
   (`lawnchair_serpent`); zoom by exactly one self-similar level using `M**t` (`paik_zoom`).
4. **Determinism.** Use `ctx.rng(salt)` (seeded), never unseeded randomness.

### Patterns

- **Thousands of copies:** make one source object (`hide_render = True`) and `geo.link_copy()` it;
  copies share mesh data. Vary per copy with `obj.color` (+ `looks.object_color` or
  `looks.tint_with_object_color` for Poly Haven materials), `Object Info > Random`, or a custom
  property read by an Attribute node (`butterfly_wing` uses `obj["wing_seed"]`).
- **Collections as instances:** for heavy sources (hair), put them in an unlinked collection and point
  empties at it (`instance_type = "COLLECTION"`); move the empties per frame.
- **Animated hue:** `World.set(hue_shift=t)`; for materials keep the Hue/Saturation node and set its
  `Hue` input each frame (`gif_tunnel`).
- **Self-similar lighting:** if a scene must look identical at different scales, make it self-lit with
  `looks.flat_emissive` so no light or shadow breaks the match.
- **Counts scale with quality:** use `ctx.count(n, minimum)`; previews use `detail = 0.25`.

## Poly Haven, through BlenderProc

- The pool is fetched on the runner by `fever/tools/fetch_haven.sh` using
  `blenderproc download haven <dir> --types ... --categories/--tags ... --resolution 1k`, cached by the
  file's hash. To make new kinds of assets available, add a `fetch ...` line there (keep filters narrow:
  whole categories can be hundreds of MB).
- `select_assets.py` matches each scene's keyword wishes against downloaded asset ids, copies only the
  chosen folders into the `fever-assets` artifact and writes `selection.json`.
- In a scene: `World(ctx, "world")` uses `bproc.world.set_world_background_hdr_img`;
  `assets.texture_material(ctx, role, fallback)` uses `bproc.loader.load_haven_mat`;
  `assets.load_model(ctx, role, height)` uses `bproc.loader.load_blend`, joins parts, and scales the
  result to `height` metres sitting on z = 0.
- **Every asset can be missing** (a filter matched nothing, or the API changed). Always provide the
  fallback (`load_model(...) or props.something()`); the run logs which assets were used and the
  gallery lists them.

## Budgets (GitHub-hosted Ubuntu runners: 4 CPU cores, no GPU)

- Cycles CPU only; no EEVEE (no GPU context headless). `standard` = 960 px wide, 24 samples + OIDN.
- Aim for **≤ 15 s per frame** at standard quality. 384 frames × 10 s ≈ 64 runner-minutes, spread over
  `shards` jobs. Up to 20 jobs run at once; each job also spends ~2-3 min on setup.
- Heavy things: hair (keep ≤ ~300k strands visible), deep transparency stacks (raise
  `transparent_bounces` only as needed), mirror regress (`glossy_bounces`), per-frame remeshing
  (≤ ~100³ grids).

## Workflow: add a scene

1. Write `fever/scenes/<id>.py` following the contract; reuse `fever/core` helpers.
2. Static checks: `python -m py_compile fever/scenes/<id>.py` and
   `cd fever/tools && python plan.py --scenes <id> --quality standard`.
3. Commit with `[skip ci]` in the message (pushes touching `tools/` or `blender/` would otherwise
   re-trigger the donut workflows) and push.
4. **Preview on GitHub:** dispatch `fever-dreams.yml` with `scenes=<id>`, `quality=preview` (one job,
   6 frames spread over the loop at 480 px). Read `render`/`assemble` logs with `get_job_logs`: look for
   `[fever]` lines (build time, per-frame seconds, assets used) and tracebacks. The contact sheet is in
   the `fever-video-<id>` artifact.
5. Fix, re-preview. Extrapolate standard cost: preview seconds per frame × ~6-8 (4× pixels, 3× samples).
6. **Publish:** dispatch with `quality=standard`, `publish=true`. The publish job commits
   `assets/fever/<id>/` and regenerates the README gallery and manifest.

## Debugging checklist

- `blenderproc` must be the first import in any script run by `blenderproc run` (`run_scene.py`, `warmup.py`).
- A Python exception makes Blender exit with code 2; the traceback is in the render job log.
- Black or empty frames: camera inside geometry, `clip_start` too large, or every pane fully transparent.
- Seam pop at the loop point: some motion has a non-integer frequency, or `frame()` reads state from a previous frame.
- `fail-on-cache-miss` in render jobs: the setup job failed before saving the Blender cache; fix setup first.
- Missing Poly Haven asset: check the setup job's `select_assets.py` output; widen keywords or the fetch filters.

## Scenes so far

`lawnchair_serpent` (fractal lawn-chair snake), `hat_tower` (bust + cowboy hats to the ceiling, mirror
regress), `hairy_julia` (4D quaternion Julia slice with hairy blobs), `lorenz_lepidoptera` (Lorenz
attractor of unique butterflies), `gif_tunnel` (GIF frames as translucent panes on a trefoil knot),
`haven_orbs` (marbles each holding a different Poly Haven world), `paik_zoom` (infinite spiral zoom into a TV).
