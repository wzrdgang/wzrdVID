# wzrdVID Agent Log

This file is the running memory for agent work on wzrdVID. It is intentionally practical and concise: future agents should use it to understand recent decisions, verification, and unresolved risks before touching the repo.

## Required Agent Behavior

Future agents must:

- Read `AGENTS.md` before every task.
- Read `docs/agent-log.md` before every task.
- Check the latest entries before making changes.
- Append a new entry after each task that changes files or makes an important decision.
- Never delete prior log entries unless explicitly instructed.
- Keep entries factual and concise.
- Include commands/checks run.
- Include unresolved risks or follow-ups.

Entries are reverse chronological: newest entry near the top.

## 2026-05-09 - v0.1.2 stabilization prep

- Agent/task: Codex / Phase 1 v0.1.2 stabilization implementation.
- Intent: Verify Lite duration/ANSI behavior, add desktop GitHub Releases update checker, bump version metadata, package release ZIP, and prepare but not publish v0.1.2.
- Files changed: `VERSION`, `app.py`, `build_app.sh`, `CHANGELOG.md`, `docs/index.html`, `docs/agent-change-playbook.md`, `docs/agent-impact-map.md`, `docs/agent-log.md`.
- Behavior changed: Yes. Desktop app now checks GitHub Releases for updates without blocking or auto-downloading.
- Commands run: `rg` stale-copy/no-upload checks; `node --check`; `python3 -m py_compile`; local Pages `curl` checks; `git diff --check`; `./build_app.sh`; `scripts/package_release.sh`; Info.plist/version/size/checksum checks.
- Checks passed: v0.1.2 verification/package checks passed during implementation.
- Checks failed: None.
- Decisions made: Lite implementation was already correct and left unchanged; release ZIP was created locally but not committed; GitHub release publication was intentionally deferred.
- Known gaps: No Sparkle, signing, notarization, or Apple pipeline work was included in this phase.
- Next recommended prompt: Publish the prepared v0.1.2 GitHub Release with the generated ZIP and SHA256.

## 2026-05-09 - Change playbook created

- Agent/task: Codex / Prompt 5 in the agent documentation system plan.
- Intent: Create a practical change-type checklist so future agents do not fly blind.
- Files changed: `AGENTS.md`, `docs/agent-change-playbook.md`, `docs/agent-log.md`.
- Behavior changed: No.
- Commands run: `git status --short --branch`; repository inspection commands; `git diff --check`; targeted `rg` section checks.
- Checks passed: Docs-only checks passed for the committed documentation set.
- Checks failed: None.
- Decisions made: The playbook is mandatory before code changes; broad refactors require explicit user direction and map/log updates.
- Known gaps: No formal markdown linter is configured in the repo.
- Next recommended prompt: Use the Future task starter prompt from the user-provided plan for the next wzrdVID task.

## 2026-05-09 - Impact map items tightened

- Agent/task: Codex / Prompt 4 in the agent documentation system plan.
- Intent: Resolve map ambiguity by searching for uppercase `Unknown` entries and replacing them with repo evidence or absent-feature statements.
- Files changed: `docs/agent-impact-map.md`, `docs/agent-log.md`.
- Behavior changed: No.
- Commands run: `rg -n "Unknown" docs/agent-impact-map.md`; additional targeted file inspections.
- Checks passed: No uppercase `Unknown` entries remain in `docs/agent-impact-map.md`.
- Checks failed: None.
- Decisions made: GitHub Actions, formal tests, backend persistence, and packaged Windows/Linux builds are documented as not present in the repo.
- Known gaps: Runtime behavior was not re-tested because this was a docs-only mapping task.
- Next recommended prompt: Create `docs/agent-change-playbook.md`.

## 2026-05-09 - Repo impact map created

- Agent/task: Codex / Prompt 3 in the agent documentation system plan.
- Intent: Create a static repo map covering desktop app modules, Lite/browser site, GitHub Pages deployment, build/package scripts, assets, and verification requirements.
- Files changed: `docs/agent-impact-map.md`, `docs/agent-log.md`.
- Behavior changed: No.
- Commands run: `find`, `rg`, `sed`, `ls`, targeted reads of Python, shell, docs, site, and asset files.
- Checks passed: Map is grounded in current repo files and records absent systems explicitly.
- Checks failed: None.
- Decisions made: The impact map treats desktop rendering/audio files, Pages/Lite files, packaging scripts, and generated assets as high-risk areas.
- Known gaps: No app runtime, PyInstaller build, or browser render smoke was run because the task was docs-only.
- Next recommended prompt: Tighten remaining map ambiguity.

## 2026-05-09 - Agent project log created

- Agent/task: Codex / Prompt 2 in the agent documentation system plan.
- Intent: Create persistent agent memory and require future agents to read and append it.
- Files changed: `docs/agent-log.md`, `AGENTS.md`.
- Behavior changed: No.
- Commands run: `sed -n` reads of `AGENTS.md`; docs-only repo inspection.
- Checks passed: `docs/agent-log.md` includes required behavior, baseline entry, entry template, and log rules.
- Checks failed: None.
- Decisions made: Agent log entries stay reverse chronological and factual; prior entries must not be deleted without explicit instruction.
- Known gaps: No historical pre-log tasks were reconstructed beyond the current agent-docs baseline.
- Next recommended prompt: Create `docs/agent-impact-map.md`.

## 2026-05-09 - Agent guide created

- Agent/task: Codex / Prompt 1 in the agent documentation system plan.
- Intent: Create a repo-specific root guide so future coding agents start with repo context, rules, commands, and verification expectations.
- Files changed: `AGENTS.md`.
- Behavior changed: No.
- Commands run: `git status --short --branch`; reads of README, docs, source files, scripts, requirements, assets, and ignored output conventions.
- Checks passed: `AGENTS.md` includes project summary, tech stack, repo structure, operating rules, safety rules, commands, validation matrix, and required task ending format.
- Checks failed: None.
- Decisions made: Future agents must preserve public branding/source-available licensing language, avoid generated output churn, and keep changes scoped.
- Known gaps: No `.github` workflows were found in the current checkout; no formal test runner/lint config was found.
- Next recommended prompt: Create `docs/agent-log.md`.

## Entry Template

```markdown
## YYYY-MM-DD - Short title

- Agent/task:
- Intent:
- Files changed:
- Behavior changed:
- Commands run:
- Checks passed:
- Checks failed:
- Decisions made:
- Known gaps:
- Next recommended prompt:
```

## Rules for Log Entries

- Use reverse chronological order, newest entry near the top.
- Do not include secrets.
- Do not paste huge logs.
- Link or name relevant files.
- Mention if deployment config, GitHub Pages, or build output was touched.
- Mention if generated files were intentionally avoided.
- Keep entries factual and concise.
