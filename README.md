# CeeloScratch

A scratch space for creative experiments driven by Claude: pipelines run on GitHub Actions
runners, and everything worth keeping is committed back here.

## Fever Dreams: BlenderProc + Poly Haven

Unexpected, programmatic, headless: each loop below is a Python scene in [`fever/scenes/`](fever/scenes/),
built with [BlenderProc](https://github.com/DLR-RM/BlenderProc) and assets that BlenderProc downloads from
[Poly Haven](https://polyhaven.com), and rendered in shards on GitHub runners by
[`.github/workflows/fever-dreams.yml`](.github/workflows/fever-dreams.yml). How to add one: [`.claude/skills/fever-dream-scene/SKILL.md`](.claude/skills/fever-dream-scene/SKILL.md).

> **Status: waiting for its first published run.** [`.github/workflows/fever-dreams.yml`](.github/workflows/fever-dreams.yml) renders
> these with BlenderProc and Poly Haven assets on GitHub runners.

## v002: luscious 48 fps, then through a 1970s CRT

[![Pink donut on a 1970s CRT, slow motion](assets/props/food/pink_donut_sprinkles/v002/renders/pink_donut_sprinkles_v002_crt_readme.webp)](assets/props/food/pink_donut_sprinkles/v002/renders/pink_donut_sprinkles_v002_crt_48fps.mp4)

*Half-speed slow motion through a simulated 1970s colour CRT. Click for the full-quality MP4
(14.57 MB, 960×720, 48 fps).*

[![Luscious pink donut, 48 fps](assets/props/food/pink_donut_sprinkles/v002/renders/pink_donut_sprinkles_v002_luscious_48fps.webp)](assets/props/food/pink_donut_sprinkles/v002/renders/pink_donut_sprinkles_v002_luscious_48fps.mp4)

*The same turn in real time with the luscious look. Click for the MP4 (1.27 MB).*

| | |
|---|---|
| **Look** | Wet, glossy icing with heavy clear coat; glamour lighting; blush backdrop; f/4 shallow focus; vanity filter |
| **Turntable** | 288 real frames, 720×540, 32 samples, 48 fps: rendered on 5 parallel macOS arm64 runners, 57-ish frames each |
| **CRT stage** | 70s film grade, lamp breathing, composite video bandwidth, 240-line beam scan, sync jitter, blooming (raster swell + defocus with brightness), barrel tube geometry, phosphor persistence, faceplate halation, slot mask, hum bar, RF snow, glass reflection and bezel |
| **Built with** | Blender 4.5.14 LTS on `arm64`, 76 MCP tool calls across all shards |
| **Workflow run** | [https://github.com/meefs/CeeloScratch/actions/runs/37269414435](https://github.com/meefs/CeeloScratch/actions/runs/37269414435) |
| **Frames rendered in** | [https://github.com/meefs/CeeloScratch/actions/runs/37266266974](https://github.com/meefs/CeeloScratch/actions/runs/37266266974) |

Everything is in [`assets/props/food/pink_donut_sprinkles/v002/`](assets/props/food/pink_donut_sprinkles/v002/): `.blend`, `.glb`, hero still, both MP4s and WebPs, posters,
`asset.json`, and one MCP transcript per render shard.

## Maiden voyage (v001): a pink donut with sprinkles

![Pink donut with sprinkles](assets/props/food/pink_donut_sprinkles/v001/renders/pink_donut_sprinkles_v001_hero.png)

![Pink donut turntable](assets/props/food/pink_donut_sprinkles/v001/renders/pink_donut_sprinkles_v001_turntable.gif)

| | |
|---|---|
| **Asset** | `pink_donut_sprinkles` / `v001`: Pink-iced donut with rainbow sprinkles, real-world scale (~9 cm diameter), Z-up in .blend, Y-up in .glb. |
| **Geometry** | 27,248 faces across 3 parts (donut_body, donut_icing, donut_sprinkles), 237 sprinkles, seed 7 |
| **Render** | CYCLES on CPU, 1600×1200, 64 samples, 198.9 s |
| **Turntable** | 48 frames, 480×360, 16 samples, 16 fps GIF, 210.8 s |
| **Built with** | Blender 4.5.14 LTS on `arm64` (macOS-26.6.2-arm64-arm-64bit) |
| **Driven by** | MCP for Blender (execute_blender_code), 11 MCP tool calls |
| **Workflow run** | [https://github.com/meefs/CeeloScratch/actions/runs/37269414435](https://github.com/meefs/CeeloScratch/actions/runs/37269414435) |

### The MCP calls that built it

| Step | MCP tool | Time |
|---|---|---|
| `get_addon_status` | `get_addon_status` | 0.06 s |
| `get_scene_info` | `get_scene_info` | 0.05 s |
| `01_reset_scene` | `execute_blender_code` | 0.02 s |
| `02_donut_body` | `execute_blender_code` | 0.09 s |
| `03_icing` | `execute_blender_code` | 0.06 s |
| `04_sprinkles` | `execute_blender_code` | 0.52 s |
| `05_stage` | `execute_blender_code` | 0.16 s |
| `06_save_and_export` | `execute_blender_code` | 200.95 s |
| `07_turntable` | `execute_blender_code` | 210.85 s |
| `get_scene_info (final)` | `get_scene_info` | 0.1 s |
| `stop_host` | `execute_blender_code` | 0.13 s |

Full requests and replies: [`mcp_transcript.json`](assets/props/food/pink_donut_sprinkles/v001/mcp_transcript.json).

## What the v001 workflow does

[`.github/workflows/maiden-voyage-donut.yml`](.github/workflows/maiden-voyage-donut.yml) runs once (on the push that adds or changes the pipeline, or manually) and:

1. **Boots an M-class runner:** `macos-latest`, GitHub's Apple Silicon (M-series) macOS runner.
2. **Installs Blender:** downloads the newest Blender 4.5 LTS build for macOS arm64 from
   download.blender.org, checks its SHA-256 against Blender's published hash, and mounts it.
3. **Starts MCP for Blender:** launches Blender headless with the
   [MCP for Blender](https://github.com/ahujasid/blender-mcp) addon serving on `localhost:9876`.
4. **Builds the donut through MCP:** an MCP client starts the `mcp-for-blender` server over stdio
   (the same way Claude Desktop or Claude Code would) and sends each recipe step as an
   `execute_blender_code` tool call: dough, icing, sprinkles, stage and lights, then render, save and
   export, then a 48-frame turntable that is stitched into a GIF.
5. **Files the results:** writes the `.blend`, `.glb`, hero render, turntable GIF, `asset.json` and MCP transcript into a
   versioned asset folder, regenerates `manifest.json` and this README, and commits them back.
6. **Ends:** Blender is shut down via MCP, logs are uploaded as a workflow artifact, and the job exits.

```
GitHub runner (macos-latest, Apple Silicon)
┌──────────────────────────────────────────────────────────────────────────────┐
│  drive_recipe.py ──stdio/MCP──▶ mcp-for-blender ──TCP :9876──▶ Blender -b     │
│  (MCP client)                   (MCP server)                    + MCP addon   │
│                                                                 (mcp_host.py) │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Why there's a `mcp_host.py`

The MCP for Blender addon normally runs inside Blender's GUI, where a UI timer executes the queued
commands. CI runners have no display, and the addon refuses to start in background mode for that
reason. `blender/mcp/mcp_host.py` loads the same addon, opens the same socket server, and runs the
addon's own command queue on Blender's main thread. The MCP server can't tell the difference.

### Timeouts: 900 seconds

`BLENDER_MCP_TIMEOUT=900` (set in the workflow) applies at every layer: the MCP client's per-call
timeout, the MCP server's wait for Blender (raised from its hardcoded 180 s by
`blender/mcp/mcp_server.py`), and the host's idle watchdog.

## File hierarchy

```
.
├── .github/workflows/maiden-voyage-donut.yml   # v001 runner job
├── .github/workflows/donut-v002-crt.yml        # v002: 5 render shards + assembly
├── assets/                                     # generated deliverables, versioned
│   └── props/food/pink_donut_sprinkles/
│       ├── v002/                                 # luscious + CRT: blend, glb, MP4s, WebPs, posters
│       └── v001/
│           ├── pink_donut_sprinkles_v001.blend # editable source scene (asset + stage)
│           ├── pink_donut_sprinkles_v001.glb   # real-time asset only (Y-up, meters)
│           ├── renders/pink_donut_sprinkles_v001_hero.png
│           ├── renders/pink_donut_sprinkles_v001_turntable.gif
│           ├── asset.json                      # parts, poly counts, render + tool versions
│           └── mcp_transcript.json             # every MCP call and reply
├── blender/
│   ├── mcp/
│   │   ├── mcp_host.py                         # runs inside Blender: hosts the MCP addon headless
│   │   ├── mcp_server.py                       # launches mcp-for-blender with the 900 s timeout
│   │   └── drive_recipe.py                     # MCP client: sends recipe steps as tool calls
│   └── recipes/
│       ├── pink_donut_sprinkles/               # v001: 01_reset_scene.py … 07_turntable.py
│       └── pink_donut_sprinkles_v002/          # v002: … 06_luscious.py, 07_save_and_export.py, 08_turntable.each.py
├── tools/
│   ├── build_manifest.py                       # writes manifest.json
│   ├── make_gif.py                             # stitches turntable frames into the GIF
│   ├── looks/                                  # v002 post: vanity.py, crt_sim.py, build_videos.sh, record_videos.py
│   └── build_readme.py                         # writes this README
├── manifest.json                               # layout + every file with size, SHA-256, role
├── .gitattributes                              # marks .blend/.glb/.png/.gif as binary
└── .gitignore
```

### v002 pipeline

[`.github/workflows/donut-v002-crt.yml`](.github/workflows/donut-v002-crt.yml) splits the 288-frame turntable across five Apple Silicon runners
(GitHub Free's limit for concurrent macOS jobs). Each runner drives Blender through MCP, sending its frames in
batches of 12 per `execute_blender_code` call (`08_turntable.each.py`), so no call nears the 900 s timeout.
Shard 0 also saves the `.blend`, `.glb` and hero still. A sixth macOS job then runs
[`tools/looks/build_videos.sh`](tools/looks/build_videos.sh):

1. `vanity.py`: soft-focus glow, glint bloom, warm blush grade, vignette, giving the luscious 48 fps MP4 and WebP.
2. Motion interpolation to twice the frames for half-speed slow motion, rebuilding the loop's seam frame.
3. `crt_sim.py`: a physical model of a 1970s colour TV, from 70s film grade and composite-video smear to a
   240-line electron beam whose spot widens with brightness, **blooming** (the raster swells and defocuses as
   the picture brightens), tube curvature, phosphor afterglow, slot mask, hum bar, static, glass and bezel.
4. Encoding: full-quality MP4, plus a lighter-static 640 px animated WebP that plays inline here.

Conventions for future assets: `assets/<category>/<subcategory>/<asset_name>/<version>/`, files named
`<asset_name>_<version>.<ext>`, recipes in `blender/recipes/<asset_name>/NN_step.py`. A new version
gets a new `vNNN` folder; old versions are never overwritten by hand.

## Running it again

Actions → **Maiden voyage: pink donut** (v001) or **Donut v002: luscious 48 fps + CRT tube** → **Run workflow**.
Pushes that change a workflow's own files also trigger it. The bots' own commits don't, so nothing loops.
