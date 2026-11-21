"""{{title}}: {{description}}"""

from __future__ import annotations

import argparse
import secrets

__version__ = "0.1.0"


def main() -> None:
    p = argparse.ArgumentParser(prog="{{name}}")
    p.add_argument("--version", action="version", version="{{name}} " + __version__)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("mcp", help="run the MCP server over stdio (local use)")
    sub.add_parser("serve", help="run the hosted MCP server over HTTP (needs {{PKG}}_API_KEYS)")
    sub.add_parser("new-key", help="print a new random API key to add to {{PKG}}_API_KEYS")
    args = p.parse_args()
    if args.cmd == "mcp":
        from .server import run_stdio

        run_stdio()
    elif args.cmd == "serve":
        from .http import serve

        serve()
    elif args.cmd == "new-key":
        print("{{pkg}}_" + secrets.token_urlsafe(24))
