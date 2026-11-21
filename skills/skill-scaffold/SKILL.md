---
name: skill-scaffold
description: Start a new Claude Code skill repo at the right level (1 instructions, 2 references, 3 scripts, 4 local MCP server, 5 hosted MCP server behind API keys), with plugin files, tests and an i-have-adhd style README/INSTALL already in place. Use when the user wants to create, start, scaffold or "skill-ify" a new skill or plugin, says "make this a skill", or has done the same task a second time.
---

# Skill scaffold

## Steps

1. **Pick the level.** Ask only what you can't infer, then choose the lowest level that works:
   - 1: Claude just needs instructions (style, process, rules).
   - 2: plus documents to consult (templates, examples, guides).
   - 3: plus deterministic steps (counting, converting, validating, filing). **Prefer this over 1-2 for
     anything with one right answer.**
   - 4: needs new tools, big dependencies, models or saved secrets on this computer.
   - 5: must work from the phone/claude.ai 24/7, or will be paid. Costs a server.
   If you're torn between two levels, tell the user the trade-off in one line and pick the lower one.

2. **Generate the repo:**

   ```bash
   python3 <this skill's dir>/scripts/scaffold.py NAME --level N --description "ONE SENTENCE" --dest ~/code/NAME
   ```

   Name: lowercase with dashes. The script prints the files it made, the next commands and the
   `claude plugin validate` result.

3. **For level 4-5, read `references/gotchas.md` before writing server code.**

4. **Fill in the TODOs** in `skills/NAME/SKILL.md` and `README.md` with the user. Write the skill's
   `description` so it says what the skill does *and* the phrases that should trigger it.

5. **Move deterministic work into scripts.** Any step that has one right answer goes in
   `skills/NAME/scripts/` (level 3+) or the server (level 4-5), with a test. `SKILL.md` keeps only the
   judgment calls.

6. **Run the next commands** the script printed (tests must pass), then hand off to **skill-ship**.

## Rules

- Never overwrite an existing folder; the script refuses unless `--force`, and you need the user's OK for that.
- Don't publish anything here. Publishing is skill-ship's job.
