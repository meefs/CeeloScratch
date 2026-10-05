"""Launch the mcp-for-blender MCP server with a configurable Blender socket timeout.

mcp-for-blender hardcodes a 180 s wait for each Blender response, which is too
short for renders on a CI runner. This launcher swaps the socket class the
server uses for one whose timeouts are raised to BLENDER_MCP_TIMEOUT
(default 900 s), then hands over to the stock server entry point.
"""

import os
import socket
import types

import blender_mcp.server as server

TIMEOUT = float(os.environ.get("BLENDER_MCP_TIMEOUT", "900"))


class _PatientSocket(socket.socket):
    def settimeout(self, value):
        super().settimeout(None if value is None else max(value, TIMEOUT))


_socket_shim = types.ModuleType("socket")
_socket_shim.__dict__.update(socket.__dict__)
_socket_shim.socket = _PatientSocket
server.socket = _socket_shim

if __name__ == "__main__":
    server.main()
