"""Tests for every skill-factory script. Run: uv run --with pytest pytest -q"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).parents[1] / "skills"


def load(rel: str):
    spec = importlib.util.spec_from_file_location(Path(rel).stem, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


scaffold = load("skill-scaffold/scripts/scaffold.py")
preflight = load("skill-ship/scripts/preflight.py")
xthread = load("x-launch/scripts/xthread.py")
teardown = load("skill-teardown/scripts/teardown.py")


# --- skill-scaffold ----------------------------------------------------------
def test_scaffold_level3_is_complete_and_clean(tmp_path):
    r = scaffold.scaffold("demo-skill", 3, "Does a demo.", tmp_path / "demo-skill", "Test Author", "tester")
    files = set(r["files"])
    assert {"skills/demo-skill/SKILL.md", "skills/demo-skill/scripts/main.py", "LICENSE",
            ".claude-plugin/plugin.json", "README.md"} <= files
    for f in (tmp_path / "demo-skill").rglob("*"):
        if f.is_file():
            assert "{{" not in f.read_text(), f
    out = subprocess.run([sys.executable, str(tmp_path / "demo-skill/skills/demo-skill/scripts/main.py"), "hi"],
                         capture_output=True, text=True, check=True).stdout
    assert json.loads(out)["length"] == 2


def test_scaffold_refuses_bad_name_and_existing_dir(tmp_path):
    import pytest

    with pytest.raises(SystemExit):
        scaffold.scaffold("Bad Name", 1, "x", tmp_path / "a", "a", "b")
    (tmp_path / "taken").mkdir()
    (tmp_path / "taken" / "f").write_text("x")
    with pytest.raises(SystemExit):
        scaffold.scaffold("ok-name", 1, "x", tmp_path / "taken", "a", "b")


# --- skill-ship ----------------------------------------------------------------
def _repo(tmp_path) -> Path:
    scaffold.scaffold("clean-skill", 3, "Clean.", tmp_path / "clean-skill", "Author", "me")
    return tmp_path / "clean-skill"


def test_preflight_passes_clean_repo(tmp_path):
    fails, _, _ = preflight.check(_repo(tmp_path), [], run_claude=False)
    assert fails == []


def test_preflight_blocks_secrets_and_flags_personal_info(tmp_path):
    repo = _repo(tmp_path)
    (repo / ".env").write_text("X=1")
    (repo / "notes.md").write_text('token = "ghp_' + "a" * 36 + '"\nAndrew Chen, call 617-555-0123, a@b.edu\n')
    fails, warns, _ = preflight.check(repo, ["Andrew Chen"], run_claude=False)
    assert any(".env" in f for f in fails)
    assert any("GitHub token" in f for f in fails)
    joined = " ".join(warns)
    assert "Andrew Chen" in joined and "617-555-0123" in joined and "a@b.edu" in joined


def test_preflight_catches_argument_placeholders(tmp_path):
    repo = _repo(tmp_path)
    skill = repo / "skills/clean-skill/SKILL.md"
    skill.write_text(skill.read_text().replace("# Clean Skill", "# Clean Skill\n\nCosts $0.015 per post. Uses $1."))
    fails, warns, _ = preflight.check(repo, [], run_claude=False)
    assert any("'$0.015" in f for f in fails)
    assert any("'$1." in w for w in warns)


# --- x-launch ------------------------------------------------------------------
def test_x_length_matches_x():
    # Both posts were accepted by X on 2026-11-21 at these lengths.
    p1 = ("Saw a Claude skill called Mira (https://github.com/Mira-AI-Tools/mira-skill) and was excited to try "
          "it, until I hit the paywall.\n\nSo I rebuilt it from scratch, free and open source. Jaz lets Claude "
          "Code watch TikTok, Reels and YouTube links on your own machine:\nhttps://github.com/lnc2131/jaz 🧵")
    assert xthread.weighted_length(p1) == 267
    assert xthread.weighted_length("一件事 👨‍👩‍👧 github.com/x") == 6 + 1 + 2 + 1 + 23
    assert xthread.weighted_length("é—“ok”") == 6  # accents, dashes and curly quotes all weigh 1


def test_x_check_cost_and_limits(tmp_path):
    t = tmp_path / "THREAD.md"
    t.write_text("hello https://a.com\n---\n" + "x" * 281 + "\n---\nmedia: /missing.mp4\nlook")
    r = xthread.check(t, premium=False)
    assert [p["cost_usd"] for p in r["posts"]] == [0.2, 0.015, 0.015]
    assert any("post 2 is 281/280" in p for p in r["problems"])
    assert any("media not found" in p for p in r["problems"])
    assert xthread.check(t, premium=True)["problems"] == ["post 3 media not found: /missing.mp4"]


# --- skill-teardown --------------------------------------------------------------
def test_teardown_spots_hidden_server_in_zip(tmp_path):
    z = tmp_path / "paid-skill.zip"
    with zipfile.ZipFile(z, "w") as f:
        f.writestr("paid/SKILL.md", "---\nname: paid\ndescription: Does things. Requires the Paid connector.\n---\n"
                                    "Call `parse_thing` with the link.\n")
    root, _ = teardown.fetch(str(z), tmp_path / "work")
    r = teardown.analyze(root)
    assert r["level"] == 1 and r["external_server"]
    assert r["skills"][0]["tools_mentioned"] == ["parse_thing"]


def test_teardown_levels_and_masking(tmp_path):
    repo = tmp_path / "r"
    (repo / "skills/s/scripts").mkdir(parents=True)
    (repo / "skills/s/SKILL.md").write_text("---\nname: s\ndescription: d\n---\n")
    (repo / "skills/s/scripts/run.py").write_text("print(1)")
    assert teardown.analyze(repo)["level"] == 3
    (repo / ".mcp.json").write_text(json.dumps({"mcpServers": {"x": {"type": "http", "url": "https://h/mcp",
                                    "headers": {"Authorization": "Bearer abcdefghijklmnopqrstuvwxyz123456"}}}}))
    r = teardown.analyze(repo)
    assert r["level"] == 5
    assert r["servers"][0]["headers"]["Authorization"] == "Bearer <masked>"


def test_teardown_refuses_zip_slip(tmp_path):
    import pytest

    z = tmp_path / "evil.zip"
    with zipfile.ZipFile(z, "w") as f:
        f.writestr("../escape.txt", "x")
    with pytest.raises(SystemExit):
        teardown.fetch(str(z), tmp_path / "work")
