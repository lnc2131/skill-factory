"""{{title}}: {{description}}"""

from __future__ import annotations

import argparse

__version__ = "0.1.0"


def main() -> None:
    p = argparse.ArgumentParser(prog="{{name}}")
    p.add_argument("--version", action="version", version="{{name}} " + __version__)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("mcp", help="run the MCP server over stdio (Claude Code starts this for you)")
    args = p.parse_args()
    if args.cmd == "mcp":
        from .server import run_stdio

        run_stdio()
