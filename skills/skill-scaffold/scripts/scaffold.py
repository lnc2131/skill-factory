#!/usr/bin/env python3
"""Create a new skill repo at a chosen level (1-5), ready for skill-ship.

  1 instructions      SKILL.md only
  2 + references      adds skills/<name>/references/
  3 + scripts         adds skills/<name>/scripts/ and a test
  4 + local server    adds a Python MCP server over stdio (uv project, `<name> mcp`)
  5 + hosted server   adds an HTTP MCP server behind API keys (header or key-in-URL)

Usage:
  python3 scaffold.py NAME --level N --description "..." [--dest DIR] [--author "..."] [--github USER]
Prints a JSON summary (files, next commands, validation result).
"""

from __future__ import annotations

import argparse
import datetime
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

TEMPLATES = Path(__file__).resolve().parents[1] / "templates"
LAYERS = [("common", 1), ("l2", 2), ("l3", 3), ("l4", 4), ("l5", 5)]
NAME_RE = re.compile(r"^[a-z][a-z0-9-]{1,40}$")


def _cmd(args: list[str]) -> str:
    try:
        return subprocess.run(args, capture_output=True, text=True, timeout=20).stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        return ""


def install_block(level: int, name: str, github: str) -> str:
    plugin = [f"claude plugin marketplace add {github}/{name}", f"claude plugin install {name}@{name}"]
    if level == 4:
        return "\n".join(["brew install uv",
                          f"uv tool install --python 3.12 git+https://github.com/{github}/{name}", *plugin])
    return "\n".join(plugin)


def next_steps(level: int, dest: Path) -> list[str]:
    if level >= 4:
        return [f"cd {dest}", "uv sync", "uv run pytest -q"]
    if level == 3:
        return [f"cd {dest}", "uv run --with pytest pytest -q"]
    return [f"cd {dest}", "edit skills/*/SKILL.md (fill the TODOs)"]


def render(text: str, values: dict[str, str]) -> str:
    for k, v in values.items():
        text = text.replace("{{" + k + "}}", v)
    return text


def scaffold(name: str, level: int, description: str, dest: Path, author: str, github: str,
             force: bool = False) -> dict:
    if not NAME_RE.match(name):
        raise SystemExit("Name must be lowercase letters, digits and dashes, starting with a letter (e.g. x-launch).")
    if not 1 <= level <= 5:
        raise SystemExit("Level must be 1 to 5.")
    if dest.exists() and any(dest.iterdir()) and not force:
        raise SystemExit(f"{dest} already exists and isn't empty. Pick another --dest or pass --force.")
    pkg = name.replace("-", "_")
    values = {
        "name": name, "pkg": pkg, "PKG": pkg.upper(), "title": name.replace("-", " ").title(),
        "description": description.replace('"', "'"), "author": author, "github": github,
        "year": str(datetime.date.today().year), "level": str(level),
        "install": install_block(level, name, github),
    }
    created: list[str] = []
    for layer, min_level in LAYERS:
        if level < min_level:
            continue
        root = TEMPLATES / layer
        for src in sorted(p for p in root.rglob("*") if p.is_file()):
            rel = str(src.relative_to(root)).replace("__name__", name).replace("__pkg__", pkg)
            out = dest / rel
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(render(src.read_text(), values))
            if out.suffix == ".py" and "scripts" in out.parts:
                out.chmod(0o755)
            if rel not in created:
                created.append(rel)
    validation = None
    if shutil.which("claude"):
        r = subprocess.run(["claude", "plugin", "validate", str(dest)], capture_output=True, text=True, timeout=60)
        validation = "passed" if r.returncode == 0 else (r.stdout + r.stderr).strip()[-500:]
    return {"dest": str(dest), "level": level, "files": sorted(created), "next": next_steps(level, dest),
            "plugin_validate": validation}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("name")
    p.add_argument("--level", type=int, required=True)
    p.add_argument("--description", required=True, help="one sentence: what the skill does")
    p.add_argument("--dest", type=Path)
    p.add_argument("--author", default=_cmd(["git", "config", "user.name"]) or "Your Name")
    p.add_argument("--github", default=_cmd(["gh", "api", "user", "--jq", ".login"]) or "YOUR-GITHUB")
    p.add_argument("--force", action="store_true")
    a = p.parse_args(argv)
    dest = (a.dest or Path.cwd() / a.name).expanduser().resolve()
    print(json.dumps(scaffold(a.name, a.level, a.description, dest, a.author, a.github, a.force), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
