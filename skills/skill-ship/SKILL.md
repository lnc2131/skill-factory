---
name: skill-ship
description: Publish a skill or plugin repo to GitHub safely and prove it installs. Scans for secrets and personal info, checks plugin and SKILL.md structure, creates the GitHub repo, pushes, installs it from GitHub like a stranger would, and writes LAUNCH.md for x-launch. Use when the user wants to ship, publish, release, open-source or push a skill/plugin to GitHub, or says a skill is ready.
---

# Skill ship

Scripts are in this skill's `scripts/` folder. Run them; don't redo their checks by reading files yourself.

## Steps

1. **Preflight:**

   ```bash
   python3 <this skill's dir>/scripts/preflight.py REPO_DIR
   ```

   - Any ✘ blocks publishing. Fix it (usually `.gitignore` or removing a value), then rerun.
   - For each ⚠, show the user the exact line and ask whether it's OK to publish. Personal details
     (names, emails, schools, resumes) are the usual problem.
   - To make private terms permanent, add them one per line to `~/.config/skill-factory/private-terms.txt`.

2. **Ask before publishing.** Show: repo name, public or private, the file count from preflight, and the
   commit message. Publishing a public repo can't really be undone (forks, caches). Wait for a clear yes.

3. **Commit and publish** (end the commit message with the attribution line your instructions require):

   ```bash
   cd REPO_DIR && git init -q -b main 2>/dev/null; git add -A && git commit -m "MESSAGE"
   gh repo create OWNER/REPO --public --source . --push --description "ONE LINE"
   ```

   If the repo already exists on GitHub, `git push` instead and say so.

4. **Prove it installs from GitHub:**

   ```bash
   python3 <this skill's dir>/scripts/verify_install.py OWNER/REPO REPO_DIR
   ```

   This installs the plugin into the user's Claude Code, so mention that first. For level 4 repos, run
   the README's `uv tool install ...` line before this. `"needs setup"` for an HTTP server is expected
   until it's deployed.

5. **Hand off:**

   ```bash
   python3 <this skill's dir>/scripts/write_launch.py REPO_DIR OWNER/REPO --pitch "WHY YOU BUILT IT"
   ```

   Ask the user for the pitch (the story, in their words). Then offer **x-launch**.

## Rules

- Never publish with a ✘ open, and never pass `--force` to git.
- If the user's ClaudeSync setup applies (a new skill under `~/.claude/skills`), mention it; a plugin
  installed from GitHub doesn't need it.
