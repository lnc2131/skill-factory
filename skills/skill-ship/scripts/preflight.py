#!/usr/bin/env python3
"""Check a skill repo is safe and complete before it goes public.

Usage: python3 preflight.py REPO_DIR [--private-terms FILE] [--no-claude]

FAIL (exit 1): secrets, secret-looking files, broken plugin/skill structure, failed `claude plugin validate`.
WARN (exit 0): emails, phone numbers, private terms (names, schools, addresses you list), files over 5 MB.
Private terms default to ~/.config/skill-factory/private-terms.txt (one per line), if it exists.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

SKIP_DIRS = {".git", ".venv", "node_modules", "__pycache__", ".pytest_cache", "data", "dist", "build"}
TEXT_LIMIT = 2_000_000
SECRET_PATTERNS = {
    "AWS key": r"AKIA[0-9A-Z]{16}",
    "GitHub token": r"gh[pousr]_[A-Za-z0-9]{36,}",
    "OpenAI/Anthropic key": r"sk-(?:ant-|proj-)?[A-Za-z0-9_-]{20,}",
    "Slack token": r"xox[abprs]-[A-Za-z0-9-]{10,}",
    "Stripe key": r"(?:sk|rk)_(?:live|test)_[A-Za-z0-9]{16,}",
    "Google API key": r"AIza[0-9A-Za-z_-]{35}",
    "Private key": r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
    "Skill API key": r"\b(?:mc|jaz|mira)_(?:sk_)?[A-Za-z0-9_-]{24,}",
    "Hard-coded secret": r"(?i)(?:api[_-]?key|secret|token|password)\s*[:=]\s*['\"][A-Za-z0-9_\-/+=]{16,}['\"]",
}
SECRET_FILES = re.compile(r"(?i)(^|/)(\.env(\..*)?|.*\.pem|.*\.p12|id_rsa.*|id_ed25519.*|secret\.key|"
                          r"credentials\.json|.*\.sqlite3?|.*\.keychain)$")
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
EMAIL_OK = re.compile(r"(?i)(noreply|no-reply|example\.(com|org)|users\.noreply\.github\.com|anthropic\.com)")
PHONE = re.compile(r"(?<!\d)(?:\+1[ .-]?)?\(?\d{3}\)?[ .-]\d{3}[ .-]\d{4}(?!\d)")


def repo_files(root: Path) -> list[Path]:
    if (root / ".git").exists():
        r = subprocess.run(["git", "-C", str(root), "ls-files", "-co", "--exclude-standard"],
                           capture_output=True, text=True)
        if r.returncode == 0:
            return [root / f for f in r.stdout.splitlines() if (root / f).is_file()]
    return [p for p in root.rglob("*") if p.is_file() and not SKIP_DIRS & set(p.relative_to(root).parts)]


def plugin_manifests(root: Path) -> list[str]:
    """plugin.json paths for every plugin the marketplace lists (`./` layout or `plugins/<name>/` layout)."""
    try:
        market = json.loads((root / ".claude-plugin/marketplace.json").read_text())
    except (OSError, json.JSONDecodeError):
        return [".claude-plugin/plugin.json"]
    out = []
    for plugin in market.get("plugins", []):
        src = plugin.get("source", "./")
        if isinstance(src, str) and src.startswith("./"):
            out.append(str(Path(src) / ".claude-plugin/plugin.json").removeprefix("./"))
    return out or [".claude-plugin/plugin.json"]


def frontmatter(text: str) -> dict[str, str]:
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    out: dict[str, str] = {}
    for line in (m.group(1).splitlines() if m else []):
        if ":" in line and not line.startswith(" "):
            k, v = line.split(":", 1)
            out[k.strip()] = v.strip()
    return out


def check(root: Path, private_terms: list[str], run_claude: bool) -> tuple[list[str], list[str], list[str]]:
    fails, warns, oks = [], [], []
    files = repo_files(root)
    oks.append(f"{len(files)} files will be published")
    terms = [t for t in private_terms if t]
    for f in files:
        rel = str(f.relative_to(root))
        if SECRET_FILES.search(rel):
            fails.append(f"secret-looking file: {rel} (add it to .gitignore)")
        size = f.stat().st_size
        if size > 5 * 1024 * 1024:
            warns.append(f"large file ({size // 1024**2} MB): {rel}")
        if size > TEXT_LIMIT:
            continue
        try:
            text = f.read_text()
        except (UnicodeDecodeError, OSError):
            continue
        for label, pat in SECRET_PATTERNS.items():
            for m in re.finditer(pat, text):
                line = text.count("\n", 0, m.start()) + 1
                fails.append(f"{label} in {rel}:{line} ({m.group(0)[:8]}…)")
        if rel.endswith("uv.lock"):
            continue
        for m in EMAIL.finditer(text):
            if not EMAIL_OK.search(m.group(0)):
                warns.append(f"email in {rel}: {m.group(0)}")
        for m in PHONE.finditer(text):
            warns.append(f"phone-like number in {rel}: {m.group(0)}")
        low = text.lower()
        for t in terms:
            if t.lower() in low:
                warns.append(f"private term '{t}' in {rel}")

    rels = {str(f.relative_to(root)) for f in files}
    for req in ("LICENSE", "README.md"):
        (oks if req in rels else fails).append(f"{req} {'present' if req in rels else 'missing'}")
    for j in [".claude-plugin/marketplace.json", *plugin_manifests(root)]:
        p = root / j
        if not p.exists():
            fails.append(f"{j} missing")
            continue
        try:
            d = json.loads(p.read_text())
            (oks if d.get("name") else fails).append(f"{j} {'valid' if d.get('name') else 'has no name'}")
        except json.JSONDecodeError as e:
            fails.append(f"{j} is not valid JSON: {e}")
    skills = sorted(root.glob("skills/*/SKILL.md")) + sorted(root.glob("plugins/*/skills/*/SKILL.md"))
    if not skills:
        fails.append("no skills/<name>/SKILL.md found")
    for s in skills:
        fm = frontmatter(s.read_text())
        rel = str(s.relative_to(root))
        if fm.get("name") != s.parent.name:
            fails.append(f"{rel}: frontmatter name '{fm.get('name')}' must match folder '{s.parent.name}'")
        desc = fm.get("description", "")
        body = s.read_text()
        for m in re.finditer(r"\$(?:\d|ARGUMENTS)\S*", body):
            line = body.count("\n", 0, m.start()) + 1
            msg = (f"{rel}:{line}: '{m.group(0)}' - Claude Code replaces $0, $1… and $ARGUMENTS in a skill "
                   "with the skill's arguments; write prices as '1.5 cents' or '0.015 USD'")
            (fails if re.match(r"\$\d+[.,]\d", m.group(0)) else warns).append(msg)
        if not desc:
            fails.append(f"{rel}: missing description")
        elif len(desc) > 1024:
            fails.append(f"{rel}: description is {len(desc)} chars (max 1024)")
        elif re.search(r"\bTODO\b(?!s)", desc + body):
            warns.append(f"{rel}: still has TODOs")
        else:
            oks.append(f"{rel}: frontmatter ok")
    if run_claude and shutil.which("claude"):
        r = subprocess.run(["claude", "plugin", "validate", str(root)], capture_output=True, text=True, timeout=90)
        if r.returncode == 0:
            oks.append("claude plugin validate passed")
        else:
            fails.append("claude plugin validate failed: " + (r.stdout + r.stderr).strip()[-300:])
    return fails, warns, oks


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("repo", type=Path)
    p.add_argument("--private-terms", type=Path, default=Path("~/.config/skill-factory/private-terms.txt"))
    p.add_argument("--no-claude", action="store_true")
    a = p.parse_args(argv)
    root = a.repo.expanduser().resolve()
    terms_file = a.private_terms.expanduser()
    terms = terms_file.read_text().splitlines() if terms_file.exists() else []
    fails, warns, oks = check(root, terms, not a.no_claude)
    for line in oks:
        print(f"✔ {line}")
    for line in dict.fromkeys(warns):
        print(f"⚠ {line}")
    for line in dict.fromkeys(fails):
        print(f"✘ {line}")
    print(f"\n{'FAIL' if fails else 'PASS'}: {len(set(fails))} problems, {len(set(warns))} warnings")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
