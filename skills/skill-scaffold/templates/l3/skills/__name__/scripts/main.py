#!/usr/bin/env python3
"""Deterministic part of {{name}}. SKILL.md calls this; it prints JSON for Claude to read.

Usage: python3 main.py <input>
"""

from __future__ import annotations

import argparse
import json
import sys


def run(text: str) -> dict:
    # TODO: replace with the real work. Keep it deterministic: same input, same output.
    return {"input": text, "length": len(text)}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("input")
    args = p.parse_args(argv)
    json.dump(run(args.input), sys.stdout, indent=2, ensure_ascii=False)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
