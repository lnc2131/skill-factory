"""{{title}} MCP server over stdio. Claude Code starts it with `{{name}} mcp`."""

from __future__ import annotations

import io
import logging
import os
import sys

import anyio
from mcp.server.mcpserver import MCPServer
from mcp.server.stdio import stdio_server
from mcp.types import ToolAnnotations

INSTRUCTIONS = "TODO: one paragraph telling the agent when to use these tools."


def build() -> MCPServer:
    mcp = MCPServer("{{name}}", instructions=INSTRUCTIONS)

    @mcp.tool(description="TODO: what this tool does and when to call it.",
              annotations=ToolAnnotations(title="Say hello", readOnlyHint=True))
    async def hello(name: str) -> str:
        return f"Hello, {name}!"

    return mcp


def run_stdio() -> None:
    """Serve MCP on the real stdout. Everything else that prints (libraries, subprocesses) goes to stderr,
    so a stray print can't corrupt the protocol stream."""
    logging.basicConfig(level=logging.INFO, stream=sys.stderr)
    protocol_fd = os.dup(1)
    os.dup2(2, 1)
    sys.stdout = sys.stderr
    out = anyio.wrap_file(io.TextIOWrapper(os.fdopen(protocol_fd, "wb", buffering=0), encoding="utf-8",
                                           write_through=True))
    mcp = build()

    async def main() -> None:
        async with stdio_server(stdout=out) as (read, write):
            server = mcp._lowlevel_server  # noqa: SLF001 - MCPServer.run() can't take a custom stdout
            await server.run(read, write, server.create_initialization_options())

    anyio.run(main)
