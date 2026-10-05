"""Write README.md from what is actually in the repo (asset metadata + MCP transcript).

The maiden-voyage workflow runs this after the build so the front page always
shows the latest render and the real numbers. Before the first build it writes
a "pending" README. Run from the repository root:

    python tools/build_readme.py
"""

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSET_DIR = Path("assets/props/food/pink_donut_sprinkles/v001")
WORKFLOW = ".github/workflows/maiden-voyage-donut.yml"


def run_link():
    server, repo, run_id = (os.environ.get(k) for k in ("GITHUB_SERVER_URL", "GITHUB_REPOSITORY", "GITHUB_RUN_ID"))
    return f"{server}/{repo}/actions/runs/{run_id}" if server and repo and run_id else None


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

## Maiden voyage: a pink donut with sprinkles

{status}

## What the workflow does

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
├── .github/workflows/maiden-voyage-donut.yml   # the runner job
├── assets/                                     # generated deliverables, versioned
│   └── props/food/pink_donut_sprinkles/
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
│   └── recipes/pink_donut_sprinkles/
│       └── 01_reset_scene.py … 07_turntable.py
├── tools/
│   ├── build_manifest.py                       # writes manifest.json
│   ├── make_gif.py                             # stitches turntable frames into the GIF
│   └── build_readme.py                         # writes this README
├── manifest.json                               # layout + every file with size, SHA-256, role
├── .gitattributes                              # marks .blend/.glb/.png/.gif as binary
└── .gitignore
```

Conventions for future assets: `assets/<category>/<subcategory>/<asset_name>/<version>/`, files named
`<asset_name>_<version>.<ext>`, recipes in `blender/recipes/<asset_name>/NN_step.py`. A new version
gets a new `vNNN` folder; old versions are never overwritten by hand.

## Running it again

Actions → **Maiden voyage: pink donut** → **Run workflow**. Any push that changes the workflow,
`blender/` or `tools/` also triggers it. The bot's own commit doesn't, so it never loops.
"""
    (ROOT / "README.md").write_text(readme)
    print("README.md written (" + ("built" if meta_path.exists() else "pending") + ")")


if __name__ == "__main__":
    main()
