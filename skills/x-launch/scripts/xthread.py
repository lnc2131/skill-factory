#!/usr/bin/env python3
"""Check an X thread before posting, and log what was posted.

  python3 xthread.py check THREAD.md [--premium]   lengths the way X counts them, cost, problems
  python3 xthread.py log LAUNCH.md URL [URL ...]    append posted URLs under "## Posts"

THREAD.md format: posts separated by a line containing only `---`. A line `media: /path/file.mp4`
inside a post attaches that file (up to 4 images, or 1 video, or 1 GIF) and isn't part of the text.

Counting follows twitter-text v3: each URL = 23, each emoji = 2, CJK and most non-Latin = 2, else 1.
Cost uses X's pay-per-use prices as of Nov 2026: $0.015 per post, $0.20 if it contains a URL.
"""

from __future__ import annotations

import argparse
import datetime
import json
import re
import sys
from pathlib import Path

LIMIT, PREMIUM_LIMIT = 280, 25_000
PRICE, PRICE_LINK = 0.015, 0.20
URL_RE = re.compile(
    r"https?://\S+|(?<![@\w.])(?:[a-z0-9-]+\.)+(?:com|org|net|io|dev|ai|app|co|me|xyz|so|gg|tv|ly|sh|tools)"
    r"(?:/\S*)?", re.I)
LIGHT = [(0, 4351), (8192, 8205), (8208, 8223), (8242, 8247)]  # twitter-text v3 weight-1 ranges


def _is_emoji(cp: int) -> bool:
    return 0x1F000 <= cp <= 0x1FAFF or 0x2600 <= cp <= 0x27BF or 0x2B00 <= cp <= 0x2BFF


def _joiner(cp: int) -> bool:  # ZWJ, variation selector, skin tones, keycap
    return cp in (0x200D, 0xFE0F, 0x20E3) or 0x1F3FB <= cp <= 0x1F3FF


def weighted_length(text: str) -> int:
    n = 0
    text = URL_RE.sub("\x00", text)  # one placeholder per URL
    prev_emoji = False
    chars = list(text)
    for i, ch in enumerate(chars):
        cp = ord(ch)
        if ch == "\x00":
            n += 23
            prev_emoji = False
        elif _joiner(cp) and prev_emoji:
            continue
        elif _is_emoji(cp):
            if prev_emoji and i > 0 and ord(chars[i - 1]) == 0x200D:
                continue  # part of a ZWJ sequence already counted
            n += 2
            prev_emoji = True
        else:
            n += 1 if any(a <= cp <= b for a, b in LIGHT) else 2
            prev_emoji = False
    return n


def parse(path: Path) -> list[dict]:
    posts = []
    for block in re.split(r"(?m)^---\s*$", path.read_text()):
        media = [ln.split(":", 1)[1].strip() for ln in block.splitlines() if ln.lower().startswith("media:")]
        text = "\n".join(ln for ln in block.splitlines() if not ln.lower().startswith("media:")).strip()
        if text or media:
            posts.append({"text": text, "media": media})
    return posts


def check(path: Path, premium: bool) -> dict:
    limit = PREMIUM_LIMIT if premium else LIMIT
    out, problems, total = [], [], 0.0
    for i, p in enumerate(parse(path), start=1):
        length = weighted_length(p["text"])
        links = len(URL_RE.findall(p["text"]))
        cost = PRICE_LINK if links else PRICE
        total += cost
        missing = [m for m in p["media"] if not Path(m).expanduser().is_file()]
        if length > limit:
            problems.append(f"post {i} is {length}/{limit}: cut {length - limit}")
        if missing:
            problems.append(f"post {i} media not found: {', '.join(missing)}")
        if len(p["media"]) > 4:
            problems.append(f"post {i} has {len(p['media'])} files (max 4 images, or 1 video/GIF)")
        out.append({"post": i, "length": length, "limit": limit, "links": links, "media": p["media"],
                    "cost_usd": cost, "text": p["text"]})
    if not out:
        problems.append("no posts found (separate posts with a line containing only ---)")
    return {"posts": out, "total_cost_usd": round(total, 3), "problems": problems, "ok": not problems}


def log(launch: Path, urls: list[str]) -> None:
    text = launch.read_text() if launch.exists() else "# Launch\n"
    if "## Posts" not in text:
        text = text.rstrip() + "\n\n## Posts\n"
    stamp = datetime.date.today().isoformat()
    text = text.rstrip() + "\n" + "\n".join(f"- {stamp} {u}" for u in urls) + "\n"
    launch.write_text(text)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check")
    c.add_argument("thread", type=Path)
    c.add_argument("--premium", action="store_true", help="X Premium allows long posts")
    lg = sub.add_parser("log")
    lg.add_argument("launch", type=Path)
    lg.add_argument("urls", nargs="+")
    a = p.parse_args(argv)
    if a.cmd == "check":
        r = check(a.thread.expanduser(), a.premium)
        for post in r["posts"]:
            media = f", {len(post['media'])} file(s)" if post["media"] else ""
            print(f"post {post['post']}: {post['length']}/{post['limit']} chars, {post['links']} link(s){media}, "
                  f"${post['cost_usd']:.3f}")
        print(f"total: ${r['total_cost_usd']:.3f} for {len(r['posts'])} post(s)")
        for prob in r["problems"]:
            print(f"✘ {prob}")
        print(json.dumps(r, ensure_ascii=False), file=sys.stderr)
        return 0 if r["ok"] else 1
    log(a.launch.expanduser(), a.urls)
    print(f"logged {len(a.urls)} post(s) in {a.launch}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
