#!/usr/bin/env python3
"""Install a published skill repo from GitHub exactly like a stranger would, and check it works.

Usage: python3 verify_install.py OWNER/REPO REPO_DIR

Reads plugin and marketplace names from REPO_DIR/.claude-plugin, then runs
`claude plugin marketplace add OWNER/REPO` and `claude plugin install PLUGIN@MARKETPLACE`,
checks `claude plugin list`, and for each server in .mcp.json checks `claude mcp get plugin:PLUGIN:SERVER`.
Prints JSON. Exit 1 if anything failed.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(list(args), capture_output=True, text=True, timeout=300)


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    slug, repo = argv[0], Path(argv[1]).expanduser()
    marketplace = json.loads((repo / ".claude-plugin/marketplace.json").read_text())
    market = marketplace["name"]
    entry = marketplace["plugins"][0]
    plugin = entry["name"]
    plugin_root = repo / entry.get("source", "./")
    out: dict = {"marketplace": market, "plugin": plugin}
    r = run("claude", "plugin", "marketplace", "add", slug)
    out["marketplace_add"] = r.returncode == 0 or "already" in (r.stdout + r.stderr).lower()
    r = run("claude", "plugin", "install", f"{plugin}@{market}")
    out["install"] = r.returncode == 0 or "already" in (r.stdout + r.stderr).lower()
    out["listed"] = f"{plugin}@{market}" in run("claude", "plugin", "list").stdout
    servers = {}
    mcp = plugin_root / ".mcp.json"
    if mcp.exists():
        for name, cfg in json.loads(mcp.read_text()).get("mcpServers", {}).items():
            got = run("claude", "mcp", "get", f"plugin:{plugin}:{name}").stdout
            servers[name] = "connected" if "Connected" in got else ("needs setup" if cfg.get("type") == "http"
                                                                  else "not connected")
    out["mcp_servers"] = servers
    out["ok"] = out["marketplace_add"] and out["install"] and out["listed"] and \
        all(v != "not connected" for v in servers.values())
    print(json.dumps(out, indent=2))
    return 0 if out["ok"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
