#!/usr/bin/env python3
"""Write LAUNCH.md: the hand-off from skill-ship to x-launch.

Usage: python3 write_launch.py REPO_DIR OWNER/REPO [--pitch "one line hook"]

Pulls the name and description from .claude-plugin/plugin.json and the install commands from
README.md's first ```bash block, so x-launch never has to re-read the repo.
"""

from __future__ import annotations

import argparse
import datetime
import json
import re
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("repo", type=Path)
    p.add_argument("slug", help="OWNER/REPO on GitHub")
    p.add_argument("--pitch", default="")
    a = p.parse_args(argv)
    repo = a.repo.expanduser().resolve()
    meta = json.loads((repo / ".claude-plugin/plugin.json").read_text())
    readme = (repo / "README.md").read_text() if (repo / "README.md").exists() else ""
    m = re.search(r"```bash\n(.*?)```", readme, re.S)
    install = m.group(1).strip() if m else f"claude plugin marketplace add {a.slug}"
    url = f"https://github.com/{a.slug}"
    text = f"""# Launch: {meta['name']}

- Repo: {url}
- Version: {meta.get('version', '0.1.0')}
- Shipped: {datetime.date.today().isoformat()}
- One-liner: {meta.get('description', '')}
- Hook: {a.pitch or 'TODO: the story in one line (why you built it)'}

## Install

```bash
{install}
```

## Posts
"""
    out = repo / "LAUNCH.md"
    out.write_text(text)
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
