"""Host the MCP-for-Blender addon inside a headless Blender (``blender -b``).

The addon's own ``BlenderMCPServer.start()`` refuses to run in background mode,
because it relies on ``bpy.app.timers`` to execute queued commands and timers
never fire without Blender's UI event loop. CI runners have no display, so this
script loads the very same addon, opens the very same socket server, and then
drives the addon's command queue from a plain loop on Blender's main thread.

From the MCP server's point of view nothing is different: it connects to
localhost:<port> and talks to the stock addon.

Usage:
    blender -b --factory-startup --python blender/mcp/mcp_host.py

Environment:
    BLENDER_MCP_ADDON    path to the addon.py bundled with mcp-for-blender (required)
    BLENDER_PORT         socket port (default 9876)
    BLENDER_MCP_TIMEOUT  seconds of client silence before the host gives up (default 900)
    MCP_HOST_READY_FILE  file touched once the socket is listening (optional)
"""

import importlib.util
import os
import socket
import sys
import threading
import time

import bpy

STOP_KEY = "mcp_host_stop"


def load_addon(path):
    spec = importlib.util.spec_from_file_location("blender_mcp_addon", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    module.register()
    return module


def start_server(addon, port):
    """Same socket setup as BlenderMCPServer.start(), minus the background-mode guard."""
    server = addon.BlenderMCPServer(host="localhost", port=port)
    server.running = True
    server.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.socket.bind((server.host, server.port))
    server.socket.listen(5)
    server.server_thread = threading.Thread(target=server._server_loop, daemon=True)
    server.server_thread.start()
    bpy.types.blendermcp_server = server
    return server


def main():
    addon_path = os.environ["BLENDER_MCP_ADDON"]
    port = int(os.environ.get("BLENDER_PORT", "9876"))
    idle_limit = float(os.environ.get("BLENDER_MCP_TIMEOUT", "900"))

    addon = load_addon(addon_path)
    server = start_server(addon, port)
    print(f"[mcp_host] Blender {bpy.app.version_string} serving MCP addon on localhost:{port}", flush=True)

    ready_file = os.environ.get("MCP_HOST_READY_FILE")
    if ready_file:
        with open(ready_file, "w") as fh:
            fh.write(str(os.getpid()))

    last_activity = time.monotonic()
    exit_code = 0
    try:
        while server.running:
            if not server.command_queue.empty():
                # Commands run here, on the main thread, exactly as the
                # addon's timer callback would run them in a GUI session.
                server._drain_command_queue()
                last_activity = time.monotonic()
            if bpy.app.driver_namespace.get(STOP_KEY):
                print("[mcp_host] stop requested by client", flush=True)
                break
            if time.monotonic() - last_activity > idle_limit:
                print(f"[mcp_host] no commands for {idle_limit:.0f}s, giving up", flush=True)
                exit_code = 1
                break
            time.sleep(0.02)
    finally:
        server.stop()
    # Hard exit: the addon leaves non-daemon helper threads behind, which would
    # otherwise keep the process alive. All files are already saved by now.
    sys.stdout.flush()
    os._exit(exit_code)


main()
