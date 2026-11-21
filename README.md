<p align="center">
  <strong>skill-factory</strong>
</p>
<p align="center">
  <strong>Skills that make skills. Idea to posted thread in an hour or two.</strong>
</p>
<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/github/license/lnc2131/skill-factory?style=flat" alt="License"></a>
</p>

> 一件事做第二次就应该 Skill 它。Skill 跑起来之后就应该尽可能地把它压成 script/program。
>
> Do something twice? Make it a Skill. Once the Skill works, squeeze it into scripts, so the AI reads less prose.

## Install

<details open>
<summary><strong>Claude Code</strong></summary>

```bash
claude plugin marketplace add lnc2131/skill-factory
claude plugin install skill-factory@skill-factory
```

Then say "make this a skill", "ship it", "launch it on X" or "how does this skill work?".

</details>

## The pipeline

Each skill owns one stage and hands a file to the next, so you can skip stages you don't need.

| Stage | Skill | Does | Hands off |
|---|---|---|---|
| Research | **skill-teardown** | Takes apart someone else's skill/plugin without running it: level, what runs on their server, license, rebuild plan | `TEARDOWN.md` |
| Build | **skill-scaffold** | Generates a repo at the right level, with plugin files, tests and README/INSTALL | Repo folder |
| Ship | **skill-ship** | Scans for secrets and personal info, publishes to GitHub, installs it from GitHub to prove the guide works | `LAUNCH.md` |
| Launch | **x-launch** | Drafts a thread, counts length exactly like X, shows cost, previews for approval, posts via [Jaz](https://github.com/lnc2131/jaz-videowatching-skill) | Post links |

## The 5 levels of a skill

| Level | Adds | Runs on | Paywall? |
|---|---|---|---|
| 1 | Instructions (`SKILL.md`) | Everywhere | No |
| 2 | Reference files | Everywhere | No |
| 3 | Scripts | Full power in Claude Code; sandboxed on claude.ai | No |
| 4 | Local MCP server / CLI | Claude Code / Desktop | No (sell setup) |
| 5 | Hosted MCP server behind API keys | Everywhere, 24/7, phone included | **Yes** |

Every skill here is level 3: a short `SKILL.md` for the judgment calls, scripts for everything with one
right answer. 9 tests cover the scripts (`uv run --with pytest pytest -q`).

## License

MIT
