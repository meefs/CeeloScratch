"""Write README.md from what is actually in the repo (asset metadata + MCP transcript).

The maiden-voyage workflow runs this after the build so the front page always
shows the latest render and the real numbers. Before the first build it writes
a "pending" README. Run from the repository root:

    python tools/build_readme.py
"""

import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSET_DIR = Path("assets/props/food/pink_donut_sprinkles/v001")
V2_DIR = Path("assets/props/food/pink_donut_sprinkles/v002")
WORKFLOW = ".github/workflows/maiden-voyage-donut.yml"
V2_WORKFLOW = ".github/workflows/donut-v002-crt.yml"
V1_WORKFLOW_NAME = "Maiden voyage: pink donut"
FEVER_DIR = Path("assets/fever")
FEVER_WORKFLOW = ".github/workflows/fever-dreams.yml"


def run_link():
    """Link to the v001 build run: the current run inside the v001 workflow, else whatever the README recorded."""
    server, repo, run_id = (os.environ.get(k) for k in ("GITHUB_SERVER_URL", "GITHUB_REPOSITORY", "GITHUB_RUN_ID"))
    if server and repo and run_id and os.environ.get("GITHUB_WORKFLOW") == V1_WORKFLOW_NAME:
        return f"{server}/{repo}/actions/runs/{run_id}"
    old = ROOT / "README.md"
    found = re.search(r"\| \*\*Workflow run\*\* \| \[(https://[^\]]+)\]", old.read_text()) if old.exists() else None
    return found.group(1) if found else None


def v2_section():
    meta_path = ROOT / V2_DIR / "asset.json"
    if not meta_path.exists() or "crt_mp4" not in json.loads(meta_path.read_text()).get("files", {}):
        return f"""> **Status: waiting for its first run.** [`{V2_WORKFLOW}`]({V2_WORKFLOW}) renders this version on
> Apple Silicon runners and fills in this section."""
    meta = json.loads(meta_path.read_text())
    f, d = meta["files"], V2_DIR.as_posix()
    calls = sum(len(json.loads((ROOT / V2_DIR / t).read_text())["calls"]) for t in f.get("mcp_transcripts", []))
    tt, sizes = meta["turntable"], meta["sizes_mb"]
    run = meta.get("workflow_run")
    rr = meta.get("render_run")
    render_row = f"\n| **Frames rendered in** | [{rr}]({rr}) |" if rr else ""
    effects = ", ".join(meta["videos"]["crt"]["effects"])
    return f"""[![Pink donut on a 1970s CRT, slow motion]({d}/{f['crt_readme_webp']})]({d}/{f['crt_mp4']})

*Half-speed slow motion through a simulated 1970s colour CRT. Click for the full-quality MP4
({sizes['crt_mp4']} MB, 960×720, 48 fps).*

[![Luscious pink donut, 48 fps]({d}/{f['luscious_webp']})]({d}/{f['luscious_mp4']})

*The same turn in real time with the luscious look. Click for the MP4 ({sizes['luscious_mp4']} MB).*

| | |
|---|---|
| **Look** | Wet, glossy icing with heavy clear coat; glamour lighting; blush backdrop; f/4 shallow focus; vanity filter |
| **Turntable** | {tt['frames']} real frames, {tt['resolution'][0]}×{tt['resolution'][1]}, {tt['samples']} samples, {tt['fps']} fps: rendered on {tt['rendered_on']} |
| **CRT stage** | {effects} |
| **Built with** | Blender {meta['built_with']['blender']} on `{meta['built_with']['machine']}`, {calls} MCP tool calls across all shards |
| **Workflow run** | {f'[{run}]({run})' if run else '`' + V2_WORKFLOW + '`'} |{render_row}

Everything is in [`{d}/`]({d}/): `.blend`, `.glb`, hero still, both MP4s and WebPs, posters,
`asset.json`, and one MCP transcript per render shard."""


def fever_section():
    scenes = sorted((json.loads(p.read_text()) for p in (ROOT / FEVER_DIR).glob("*/scene.json")
                     if "mp4" in json.loads(p.read_text()).get("files", {})), key=lambda m: m["title"])
    if not scenes:
        return f"""> **Status: waiting for its first published run.** [`{FEVER_WORKFLOW}`]({FEVER_WORKFLOW}) renders
> these with BlenderProc and Poly Haven assets on GitHub runners."""
    blocks = []
    for m in scenes:
        d = (FEVER_DIR / m["id"]).as_posix()
        f = m["files"]
        haven = m.get("haven_assets", {})
        used = sorted({rel.split("/")[1] for kind in ("hdri", "texture", "model") for rel in haven.get(kind, {}).values()}
                      | {rel.split("/")[1] for rel in haven.get("hdri_pool", [])})
        assets_line = ", ".join(f"`{u}`" for u in used) if used else "procedural only"
        if "gif" in haven:
            assets_line += f"; GIF: {haven['gif'].get('source')}"
        run = m.get("workflow_run")
        blocks.append(f"""### {m['title']}

[![{m['title']}]({d}/{f['preview_webp']})]({d}/{f['mp4']})

{m['logline']}

*{m['seconds']} s loop at {m['fps']} fps, {m['resolution'][0]}×{m['resolution'][1]}, {m['samples']} samples;
{m['render_seconds_per_frame']} s per frame across {m['shards']} runners ({m['blender']}). Poly Haven: {assets_line}.
Click for the MP4 ({m['sizes_mb']['mp4']} MB){f' · [workflow run]({run})' if run else ''}.*""")
    return "\n\n".join(blocks)


def other_section():
    """Any other MP4 under assets/ that has a <stem>_preview.webp (made by tools/make_previews.py)."""
    from make_previews import covered
    skip = covered()
    blocks = []
    for mp4 in sorted((ROOT / "assets").glob("**/*.mp4")):
        preview = mp4.with_name(f"{mp4.stem}_preview.webp")
        if mp4.resolve() in skip or not preview.exists():
            continue
        rel, prev = mp4.relative_to(ROOT).as_posix(), preview.relative_to(ROOT).as_posix()
        blocks.append(f"[![{mp4.stem}]({prev})]({rel})\n\n`{rel}`")
    if not blocks:
        return ""
    return "## More renders\n\nEvery other video in `assets/`, auto-previewed by `.github/workflows/readme-sync.yml`.\n\n" + \
        "\n\n".join(blocks) + "\n\n"


def built_section(meta, transcript):
    files = meta["files"]
    parts = meta["parts"]
    faces = sum(p["faces"] for p in parts.values())
    built = meta["built_with"]
    render = meta["render"]
    calls = transcript.get("calls", [])
    link = run_link()
    rows = "\n".join(f"| `{c['step']}` | `{c['tool']}` | {c['seconds']} s |" for c in calls)
    tt = meta.get("turntable")
    gif = files.get("turntable_gif")
    spin = (f"\n\n![Pink donut turntable]({ASSET_DIR.as_posix()}/{gif})" if gif else "")
    tt_row = (f"\n| **Turntable** | {tt['frames']} frames, {tt['resolution'][0]}×{tt['resolution'][1]}, "
              f"{tt['samples']} samples, {tt['fps']} fps GIF, {tt['seconds']} s |" if tt and gif else "")
    return f"""![Pink donut with sprinkles]({ASSET_DIR.as_posix()}/{files['hero_render']}){spin}

| | |
|---|---|
| **Asset** | `{meta['asset']}` / `{meta['version']}`: {meta['description']} |
| **Geometry** | {faces:,} faces across {len(parts)} parts ({', '.join(parts)}), {meta['sprinkle_count']} sprinkles, seed {meta['seed']} |
| **Render** | {render['engine']} on {render['device']}, {render['resolution'][0]}×{render['resolution'][1]}, {render['samples']} samples, {render['seconds']} s |{tt_row}
| **Built with** | Blender {built['blender']} on `{built['machine']}` ({built['os']}) |
| **Driven by** | {built['control']}, {len(calls)} MCP tool calls |
| **Workflow run** | {f'[{link}]({link})' if link else '`' + WORKFLOW + '`'} |

### The MCP calls that built it

| Step | MCP tool | Time |
|---|---|---|
{rows}

Full requests and replies: [`mcp_transcript.json`]({ASSET_DIR.as_posix()}/mcp_transcript.json)."""


PENDING = f"""> **Status: waiting for the first run.** The `{WORKFLOW}` workflow builds the donut on a
> GitHub macOS (Apple Silicon) runner and rewrites this README with the render and real numbers."""


def main():
    meta_path = ROOT / ASSET_DIR / "asset.json"
    transcript_path = ROOT / ASSET_DIR / "mcp_transcript.json"
    if meta_path.exists():
        transcript = json.loads(transcript_path.read_text()) if transcript_path.exists() else {}
        status = built_section(json.loads(meta_path.read_text()), transcript)
    else:
        status = PENDING

    readme = f"""# CeeloScratch

A scratch space for creative experiments driven by Claude: pipelines run on GitHub Actions
runners, and everything worth keeping is committed back here.

## Fever Dreams: BlenderProc + Poly Haven

Unexpected, programmatic, headless: each loop below is a Python scene in [`fever/scenes/`](fever/scenes/),
built with [BlenderProc](https://github.com/DLR-RM/BlenderProc) and assets that BlenderProc downloads from
[Poly Haven](https://polyhaven.com), and rendered in shards on GitHub runners by
[`{FEVER_WORKFLOW}`]({FEVER_WORKFLOW}). How to add one: [`.claude/skills/fever-dream-scene/SKILL.md`](.claude/skills/fever-dream-scene/SKILL.md).

{fever_section()}

{other_section()}## v002: luscious 48 fps, then through a 1970s CRT

{v2_section()}

## Maiden voyage (v001): a pink donut with sprinkles

{status}

## What the v001 workflow does

[`{WORKFLOW}`]({WORKFLOW}) runs once (on the push that adds or changes the pipeline, or manually) and:

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

[`{V2_WORKFLOW}`]({V2_WORKFLOW}) splits the 288-frame turntable across five Apple Silicon runners
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
"""
    (ROOT / "README.md").write_text(readme)
    print("README.md written (" + ("built" if meta_path.exists() else "pending") + ")")


if __name__ == "__main__":
    main()
