# Running Cloud Agents Against This Repo

How to hand work to a Claude cloud agent (a "routine") so it runs while the
laptop is closed — and how to recover when something goes sideways. Written
after the first attempt (2026-06-11) hit every interesting failure mode.

## One-time setup (the thing that bit us)

The cloud sandbox authenticates to GitHub through the **Claude GitHub App**,
NOT through your local `gh` credentials. For a private repo, the app must be
granted access **before** any routine runs:

1. Go to [claude.ai/code](https://claude.ai/code) → settings → GitHub (or
   [github.com/apps/claude](https://github.com/apps/claude)).
2. Install / configure the Claude GitHub App and grant it
   `Dev-Ray-Hunt/embroidery-processing` (repo-scoped is fine).

**Symptoms of missing access:**
- The routine dies instantly with `ended_reason: auto_disabled_repo_access`
  (and disables itself — re-enable it after fixing access), **or**
- The agent runs but cannot push; a well-instructed agent then leaves a
  **git bundle** + hand-off instructions (see Recovery below).

## Creating a routine

Easiest: ask Claude Code locally — "schedule a cloud agent to do X at TIME"
(it uses the `/schedule` skill). Or use the dashboard:
[claude.ai/code/routines](https://claude.ai/code/routines).

- Times are **UTC** in the API; say your local time and let Claude convert.
- One-time runs auto-disable after firing (`run_once_fired` = success-path).
- Strip MCP connectors unless the task needs them — routines attach all of
  your claude.ai connectors by default, and repo work needs none.
- Default model `claude-sonnet-4-6` is right for well-specified tasks.

## Prompt checklist (cloud agents start with ZERO context)

A good brief for this repo includes:

- [ ] Pointer to the spec: the relevant `pocs/*/NEXT.md` + root `POC_*.md`.
- [ ] **Data bootstrap**: `data/` is gitignored and arrives empty. Madeira
      sources re-fetch via the script in `data/README.md`. DST samples are
      NOT obtainable in the cloud (Tier 2/3 are local-only by policy) — say
      explicitly that DST-dependent tests skipping is expected.
- [ ] Environment fallbacks: Linux sandbox; if `uv sync` fights pycairo,
      `apt-get install -y libcairo2-dev pkg-config`; Playwright browsers may
      be absent (those tests skip).
- [ ] Branch name to use, and **"open a PR, do not merge"**.
- [ ] The standards block: commit per green milestone, ruff check+format,
      full suite before push, honest failure policy (ship what works,
      document what failed).
- [ ] **Push-failure fallback**: "If you cannot push to GitHub, create a git
      bundle of your branch (`git bundle create <name>.bundle <branch>`),
      surface it as a downloadable artifact, and print exact hand-off
      commands."

## Known sandbox limitations (observed 2026-06-11)

- `madeira.com` PDFs were unreachable from the sandbox (CDN/geo blocking) —
  the agent correctly built a reduced 706-thread catalogue from the GPL
  sources only. Numbers derived in the cloud against the reduced catalogue
  should be re-run locally against the full 823-thread build before they go
  in FINDINGS.
- Team DSTs never exist in the cloud (by design — they stay on Brandon's
  machine). Cloud agents can only do data-light work: POC 2, docs, pure
  algorithms, refactors.

## Recovery: integrating a bundle hand-off

When the agent leaves a `.bundle` instead of a pushed branch:

1. Download the bundle from the cloud session's file browser at
   [claude.ai/code](https://claude.ai/code) (open the session → files).
2. In the local repo:
   ```bash
   git fetch ~/Downloads/<name>.bundle <branch>:<branch>
   git checkout <branch>
   uv sync && uv run pytest -q        # verify BEFORE pushing — the cloud
                                      # env differed from ours
   ```
3. Re-run anything the sandbox computed against reduced data (e.g.
   benchmarks against the full catalogue) and update the docs the agent
   wrote if numbers change.
4. Push with the keychain workaround if plain push hangs:
   ```bash
   GIT_TERMINAL_PROMPT=0 git -c credential.helper= \
     -c credential.helper='!gh auth git-credential' push -u origin <branch>
   ```
5. Open the PR using the agent's prepared body (edit numbers first if step 3
   changed them).
