"""Build an asset by driving Blender through the MCP-for-Blender server.

This is a scripted MCP client. It launches the MCP server over stdio (exactly
how Claude Desktop / Claude Code would), checks the connection with the
server's own status tools, then sends each recipe step as an
``execute_blender_code`` tool call. Every call and its reply is written to a
transcript so the build can be audited later.

Steps named ``NN_name.each.py`` are sent once per batch of turntable frames
(``PARAMS["batch"]`` holds that call's frame indices), so long renders are split
into calls that each stay well inside the MCP timeout. ``--frame-range`` limits
those frames to one shard when the render is spread over several runners.

Usage:
    python blender/mcp/drive_recipe.py \
        --recipe blender/recipes/pink_donut_sprinkles \
        --output-dir assets/props/food/pink_donut_sprinkles/v001 \
        --asset-name pink_donut_sprinkles --version v001
"""

import argparse
import asyncio
import json
import os
import sys
import time
from datetime import timedelta
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

HERE = Path(__file__).resolve().parent
TIMEOUT = float(os.environ.get("BLENDER_MCP_TIMEOUT", "900"))
DEFAULT_PROMPT = "Creates a pink donut with sprinkles, saves it within a well defined file hierarchy for later usage"
STOP_CODE = 'bpy.app.driver_namespace["mcp_host_stop"] = True\nprint("bye")'


def text_of(result):
    return "\n".join(getattr(part, "text", "") for part in result.content).strip()


async def call(session, transcript, tool, arguments, label=None):
    started = time.monotonic()
    result = await session.call_tool(tool, arguments, read_timeout_seconds=timedelta(seconds=TIMEOUT))
    seconds = round(time.monotonic() - started, 2)
    reply = text_of(result)
    ok = not result.isError and not reply.startswith(("Error", "Rejected"))
    transcript.append({"tool": tool, "step": label or tool, "seconds": seconds, "ok": ok,
                       "arguments": arguments, "reply": reply[:4000]})
    print(f"[mcp] {label or tool}: {'ok' if ok else 'FAILED'} in {seconds}s", flush=True)
    for line in reply.splitlines()[:20]:
        print(f"      {line}", flush=True)
    if not ok:
        raise RuntimeError(f"{label or tool} failed:\n{reply}")
    return reply


async def run(args):
    user_prompt = args.user_prompt
    output_dir = Path(args.output_dir).resolve()
    params = {
        "asset_name": args.asset_name,
        "version": args.version,
        "file_stem": f"{args.asset_name}_{args.version}",
        "output_dir": str(output_dir),
        "seed": args.seed,
        "render": {"width": args.width, "height": args.height, "samples": args.samples},
        "turntable": {"frames": args.turntable_frames, "fps": args.turntable_fps,
                      "width": args.turntable_width, "height": args.turntable_height,
                      "samples": args.turntable_samples, "frames_dir": str(Path(args.frames_dir).resolve())},
    }
    steps = [p for p in sorted(Path(args.recipe).glob("[0-9][0-9]_*.py")) if p.name.split(".")[0] not in args.skip]
    if not steps:
        sys.exit(f"no recipe steps found in {args.recipe}")
    start, _, end = (args.frame_range or f"0:{args.turntable_frames}").partition(":")
    frames = list(range(int(start), int(end)))
    batches = [frames[i:i + args.batch_size] for i in range(0, len(frames), args.batch_size)]

    def calls_for(step):
        """(label, code) pairs for one step: one call, or one per frame batch for .each steps."""
        name = step.name[:-3]
        if not name.endswith(".each"):
            yield name, f"import json\nPARAMS = json.loads({json.dumps(params)!r})\n" + step.read_text()
            return
        for n, batch in enumerate(batches, 1):
            p = dict(params, batch=batch)
            yield (f"{name[:-5]} [{n}/{len(batches)}: frames {batch[0]}-{batch[-1]}]",
                   f"import json\nPARAMS = json.loads({json.dumps(p)!r})\n" + step.read_text())

    env = dict(os.environ, DISABLE_TELEMETRY="true", BLENDER_MCP_TIMEOUT=str(TIMEOUT))
    server = StdioServerParameters(command=sys.executable, args=[str(HERE / "mcp_server.py")], env=env)
    transcript = []
    try:
        async with stdio_client(server) as (read, write):
            async with ClientSession(read, write, read_timeout_seconds=timedelta(seconds=TIMEOUT)) as session:
                init = await session.initialize()
                tools = await session.list_tools()
                print(f"[mcp] connected to {init.serverInfo.name} {init.serverInfo.version}, "
                      f"{len(tools.tools)} tools", flush=True)
                await call(session, transcript, "get_addon_status", {"user_prompt": user_prompt})
                await call(session, transcript, "get_scene_info", {"user_prompt": user_prompt})
                try:
                    for step in steps:
                        for label, code in calls_for(step):
                            await call(session, transcript, "execute_blender_code",
                                       {"code": code, "user_prompt": user_prompt}, label=label)
                    await call(session, transcript, "get_scene_info", {"user_prompt": user_prompt},
                               label="get_scene_info (final)")
                finally:
                    await call(session, transcript, "execute_blender_code",
                               {"code": STOP_CODE, "user_prompt": user_prompt}, label="stop_host")
    finally:
        if args.transcript:
            Path(args.transcript).parent.mkdir(parents=True, exist_ok=True)
            Path(args.transcript).write_text(json.dumps(
                {"server": "mcp-for-blender", "timeout_seconds": TIMEOUT, "calls": transcript},
                indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--recipe", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--asset-name", required=True)
    parser.add_argument("--version", default="v001")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--width", type=int, default=1600)
    parser.add_argument("--height", type=int, default=1200)
    parser.add_argument("--samples", type=int, default=128)
    parser.add_argument("--turntable-frames", type=int, default=48)
    parser.add_argument("--turntable-fps", type=int, default=16)
    parser.add_argument("--turntable-width", type=int, default=480)
    parser.add_argument("--turntable-height", type=int, default=360)
    parser.add_argument("--turntable-samples", type=int, default=16)
    parser.add_argument("--frames-dir", default="logs/turntable_frames",
                        help="scratch folder for turntable frames (not committed)")
    parser.add_argument("--frame-range", help="START:END turntable frames for this shard (default: all)")
    parser.add_argument("--batch-size", type=int, default=12, help="frames per MCP call for .each steps")
    parser.add_argument("--skip", nargs="*", default=[], help="step names to leave out, e.g. 07_save_and_export")
    parser.add_argument("--user-prompt", default=DEFAULT_PROMPT)
    parser.add_argument("--transcript")
    asyncio.run(run(parser.parse_args()))


if __name__ == "__main__":
    main()
