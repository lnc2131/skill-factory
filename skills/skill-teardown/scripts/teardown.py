#!/usr/bin/env python3
"""Inventory someone else's skill or plugin without running any of it, and classify its level (1-5).

Usage:
  python3 teardown.py TARGET [--out TEARDOWN.md]

TARGET is one of:
  path/to/skill.zip            a downloaded skill archive
  path/to/folder               a checked-out repo or unzipped skill
  github:OWNER/REPO            or https://github.com/OWNER/REPO (shallow clone, nothing executed)
  plugin:NAME                  a plugin already installed in Claude Code

Prints Markdown: files with SHA-256, skills and their triggers, MCP servers (secrets masked), auth,
scripts, native binaries, level, where the value lives, and what a rebuild needs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

SKIP = {".git", "node_modules", ".venv", "__pycache__"}
SCRIPT_EXT = {".py", ".js", ".mjs", ".ts", ".sh", ".rb", ".go", ".rs"}
MAGIC = {b"\x7fELF": "ELF", b"\xcf\xfa\xed\xfe": "Mach-O", b"\xca\xfe\xba\xbe": "Mach-O universal", b"MZ": "PE"}
LEVELS = {1: "instructions only", 2: "+ reference files", 3: "+ scripts", 4: "+ local MCP server / CLI",
          5: "+ hosted MCP server"}


def mask(value: str) -> str:
    """Keep template variables and URLs readable; hide anything that looks like a real secret."""
    return re.sub(r"(?<![{.])\b[A-Za-z0-9_\-]{24,}\b(?!})", "<masked>", value)


def fetch(target: str, work: Path) -> tuple[Path, str]:
    if target.startswith(("github:", "https://github.com/")):
        slug = target.removeprefix("github:").removeprefix("https://github.com/").strip("/")
        dest = work / "repo"
        subprocess.run(["git", "clone", "--depth", "1", "--quiet", f"https://github.com/{slug}.git", str(dest)],
                       check=True, timeout=180)
        return dest, f"github.com/{slug}"
    if target.startswith("plugin:"):
        name = target.removeprefix("plugin:")
        hits = sorted(Path("~/.claude/plugins/cache").expanduser().glob(f"*/{name}/*/"))
        if not hits:
            raise SystemExit(f"No installed plugin named {name!r} in ~/.claude/plugins/cache")
        return hits[-1], f"installed plugin {name} ({hits[-1].name})"
    p = Path(target).expanduser()
    if p.is_file() and zipfile.is_zipfile(p):
        dest = work / "zip"
        with zipfile.ZipFile(p) as z:
            for m in z.infolist():  # refuse path traversal
                if m.filename.startswith("/") or ".." in Path(m.filename).parts:
                    raise SystemExit(f"Refusing unsafe path in zip: {m.filename}")
            z.extractall(dest)
        return dest, p.name
    if p.is_dir():
        return p, str(p)
    raise SystemExit(f"Can't read {target!r}: not a zip, folder, github:OWNER/REPO or plugin:NAME")


def frontmatter(text: str) -> dict[str, str]:
    m = re.match(r"^---\n(.*?)\n---", text, re.S)
    out = {}
    for line in (m.group(1).splitlines() if m else []):
        if ":" in line and not line.startswith(" "):
            k, v = line.split(":", 1)
            out[k.strip()] = v.strip().strip('"')
    return out


def analyze(root: Path) -> dict:
    files = [p for p in sorted(root.rglob("*")) if p.is_file() and not SKIP & set(p.relative_to(root).parts)]
    inv, scripts, binaries, refs = [], [], [], []
    for f in files:
        rel = str(f.relative_to(root))
        data = f.read_bytes()
        inv.append((rel, len(data), hashlib.sha256(data).hexdigest()[:16]))
        kind = next((v for k, v in MAGIC.items() if data.startswith(k)), None)
        if kind:
            binaries.append(f"{rel} ({kind})")
        elif f.suffix in SCRIPT_EXT:
            scripts.append(rel)
        elif "references" in f.parts or "assets" in f.parts or "templates" in f.parts:
            refs.append(rel)
    skills = []
    for s in [f for f in files if f.name == "SKILL.md"]:
        text = s.read_text(errors="replace")
        fm = frontmatter(text)
        tools = sorted(set(re.findall(r"`([a-z][a-z0-9_]{2,})`\s*(?:tool|with)", text)) |
                       set(re.findall(r"[Cc]all (?:the )?`([a-z][a-z0-9_]{2,})`", text)))
        skills.append({"path": str(s.relative_to(root)), "name": fm.get("name", "?"),
                       "description": fm.get("description", ""), "words": len(text.split()),
                       "tools_mentioned": tools,
                       "needs_connector": bool(re.search(r"(?i)connector|mcp server|api key|subscription", text))})
    servers, user_config = [], {}
    for f in [f for f in files if f.name in (".mcp.json", "mcp.json", "plugin.json")]:
        try:
            d = json.loads(f.read_text())
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        user_config.update(d.get("userConfig", {}))
        for name, cfg in (d.get("mcpServers") or {}).items():
            kind = cfg.get("type") or ("http" if cfg.get("url") else "stdio")
            servers.append({"file": str(f.relative_to(root)), "name": name, "type": kind,
                            "url": mask(cfg.get("url", "")),
                            "command": mask(" ".join([cfg.get("command", ""), *cfg.get("args", [])]).strip()),
                            "headers": {k: mask(v) for k, v in (cfg.get("headers") or {}).items()}})
    hooks = [str(f.relative_to(root)) for f in files if f.name == "hooks.json"]
    license_file = next((f for f in files if f.name.upper().startswith(("LICENSE", "COPYING"))), None)
    license_name = None
    if license_file:
        head = license_file.read_text(errors="replace")[:300]
        license_name = next((n for n in ("MIT", "Apache", "GPL", "BSD", "MPL", "ISC") if n in head), "custom")
    if any(s["type"] == "http" for s in servers):
        level = 5
    elif servers or binaries:
        level = 4
    elif scripts:
        level = 3
    elif refs:
        level = 2
    else:
        level = 1
    external = level < 5 and any(s["needs_connector"] or s["tools_mentioned"] for s in skills) and not servers
    return {"files": inv, "skills": skills, "servers": servers, "user_config": user_config, "scripts": scripts,
            "binaries": binaries, "references": refs, "hooks": hooks, "license": license_name,
            "level": level, "external_server": external}


def report(r: dict, label: str) -> str:
    lv = r["level"]
    lines = [f"# Teardown: {label}", ""]
    if r["external_server"]:
        lines += [f"**Level: 5 in practice.** This package is level {lv} ({LEVELS[lv]}), but its skill calls "
                  "tools that aren't included here, so they come from a connector/server you don't get.", ""]
    else:
        lines += [f"**Level: {lv}** ({LEVELS[lv]})", ""]
    auth = [s for s in r["servers"] if s["headers"]] or r["user_config"]
    where = ("on their server: the files are free to read, the hosted tools are the product"
             if lv == 5 or r["external_server"] else
             "in the files you have: the instructions and code are all here")
    lines += [f"- Value lives: {where}",
              f"- Auth: {'API key (' + ', '.join(r['user_config']) + ')' if r['user_config'] else ('headers' if auth else 'none')}",
              f"- License: {r['license'] or 'none found (all rights reserved by default: rebuild, do not copy)'}",
              f"- Files: {len(r['files'])}, scripts: {len(r['scripts'])}, native binaries: {len(r['binaries'])}, "
              f"hooks: {len(r['hooks'])}", ""]
    for s in r["skills"]:
        lines += [f"## Skill `{s['name']}` ({s['path']}, {s['words']} words)", "", f"> {s['description']}", ""]
        if s["tools_mentioned"]:
            lines.append(f"Tools it calls: {', '.join('`' + t + '`' for t in s['tools_mentioned'])}")
        lines.append("")
    if r["servers"]:
        lines += ["## MCP servers", ""]
        for s in r["servers"]:
            target = s["url"] or s["command"]
            hdr = f", headers: {s['headers']}" if s["headers"] else ""
            lines.append(f"- `{s['name']}` ({s['type']}): {target}{hdr}  [{s['file']}]")
        lines.append("")
    if r["binaries"]:
        lines += ["## Native binaries (inspect with REA, never run)", "", *[f"- {b}" for b in r["binaries"]], ""]
    if r["scripts"]:
        lines += ["## Scripts (read, don't run)", "", *[f"- {s}" for s in r["scripts"][:40]], ""]
    lines += ["## Files", "", "| File | Bytes | SHA-256 (first 16) |", "|---|---|---|"]
    lines += [f"| {f} | {n:,} | `{h}` |" for f, n, h in r["files"][:80]]
    if len(r["files"]) > 80:
        lines.append(f"| … {len(r['files']) - 80} more | | |")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("target")
    p.add_argument("--out", type=Path)
    p.add_argument("--json", action="store_true", help="print the raw analysis as JSON instead")
    a = p.parse_args(argv)
    with tempfile.TemporaryDirectory(prefix="teardown-") as tmp:
        root, label = fetch(a.target, Path(tmp))
        r = analyze(root)
        out = json.dumps(r, indent=2) if a.json else report(r, label)
    if a.out:
        a.out.write_text(out)
        print(a.out)
    else:
        print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
