---
name: review-pr
description: >
  Reviews the changes a branch introduces — the diff of the current
  branch (HEAD) against a base branch, `develop` by default — by
  orchestrating this repository's specialised review agents:
  `jwt-allauth-security-reviewer` (session and token invariants, and
  delegating to allauth), `jwt-allauth-efficiency-reviewer` (the
  stateless path, the rotation lock, simplicity) and
  `jwt-allauth-surface-reviewer` (backwards compatibility of settings and
  endpoints, documentation, release notes, and the claims that go stale).
  Computes the diff from the merge base (three-dot, the way GitHub shows
  a PR), picks the agents the diff actually concerns, launches them IN
  PARALLEL, and aggregates their findings into one report ordered by
  severity with an overall verdict. Optionally takes the base branch as
  an argument: `/review-pr main` compares against `main` instead of
  `develop`. Read-only: it audits and reports; it changes nothing. Use it
  before opening or merging a pull request, or whenever you want a full
  review of a branch. Triggers on: "review the PR", "review-pr", "review
  the branch changes", "review the diff", "review this branch against X".
arguments: [base_branch]
argument-hint: "[base-branch] — default develop, e.g. main"
allowed-tools: >
  Agent
  Read
  Grep
  Glob
  Bash(git diff *)
  Bash(git log *)
  Bash(git merge-base *)
  Bash(git rev-parse *)
  Bash(git branch *)
  Bash(git fetch *)
  Bash(git status *)
model: opus
---

# Review PR — reviewing a branch through the repository's agents

Reviewing a change to this library covers three independent dimensions,
and each has its own read-only auditor in `.claude/agents/`. A single
prompt trying to check all three at once dilutes every one of them, so
this skill **delegates each dimension to its specialist** and aggregates
the results.

The skill **orchestrates**: it resolves the base branch, computes the PR
diff, decides which agents apply, launches them **in parallel** and
consolidates their reports. It does **not** review the code itself — that
work lives in the agents. It is **read-only**: neither the skill nor its
agents modify code or documentation; they propose the fix, they do not
apply it.

**What this skill deliberately does not cover:** general correctness,
naming, dead code and style. `/code-review` and `/simplify` already do
that, and duplicating them here would produce two reports arguing about
the same lines. The three agents carry the same rule and refer such
findings on rather than developing them.

## Input

`$ARGUMENTS` optionally holds the **base branch** to compare against:

- *(empty)* → compares `HEAD` against **`develop`** (the default).
- `main` → compares `HEAD` against `main`.

The branch under review is always the current one (`HEAD`); the argument
only changes the **base**. Do not expect a second argument.

## Execution

### Step 1 — Resolve the base branch and the diff range

1. `base = $ARGUMENTS` after `trim`; if empty, `base = develop`.
2. Resolve the real reference, preferring the remote (it is closer to
   what the PR will show):
   - Refresh, best-effort and non-blocking: `git fetch origin <base>`. If
     the network fails, retry with backoff (2s, 4s, 8s, 16s) per this
     environment's git rules, then carry on with what is local.
   - Use `origin/<base>` if it verifies (`git rev-parse --verify
     origin/<base>`); otherwise the local `<base>`.
   - If **neither** exists → stop and ask for a valid base, listing the
     candidates with `git branch -a`. Do not invent one.
3. `head = git rev-parse --abbrev-ref HEAD`. If it equals the resolved
   base, say there is nothing to review and stop.
4. **Always use the three-dot range** `BASE...HEAD`. Three-dot starts at
   the *merge base*, so the diff holds only what this branch introduces,
   not what the base gained after they parted — which is exactly what
   GitHub shows in a PR. Never use the two-dot `BASE HEAD`: it would
   contaminate the review with changes nobody on this branch wrote.

### Step 2 — Collect and classify the diff

Run these and record the PR context:

- `git diff --stat BASE...HEAD` — files and volume.
- `git diff --name-only BASE...HEAD` — the file list.
- `git log BASE..HEAD --oneline` — the commits in the PR.

No changed files → report "no changes against `<base>`" and stop.

Classify each changed file, because the classification decides which
agents run:

| Kind | Pattern |
| --- | --- |
| Token layer | `jwt_allauth/tokens/**` |
| Authentication | `jwt_allauth/authentication.py`, `jwt_allauth/permissions.py`, `jwt_allauth/csrf.py`, `jwt_allauth/revocation.py` |
| Endpoints | `jwt_allauth/*/views.py`, `jwt_allauth/*/serializers.py`, `jwt_allauth/*/urls.py`, `jwt_allauth/urls.py` |
| Adapters | `jwt_allauth/adapter.py`, `jwt_allauth/*/adapter.py` |
| Shared helpers | `jwt_allauth/utils.py`, `jwt_allauth/accounts.py`, `jwt_allauth/mfa/gate.py`, `jwt_allauth/throttling.py`, `jwt_allauth/exceptions.py` |
| Startup config | `jwt_allauth/apps.py`, `jwt_allauth/checks.py`, `jwt_allauth/constants.py` |
| Models | `jwt_allauth/**/models.py` |
| Schema | `jwt_allauth/schema.py` |
| Packaging | `pyproject.toml`, `tox.ini`, `setup.cfg`, `dev-requirements.txt`, `.github/**` |
| Scaffolder | `jwt_allauth/bin/**` |
| Templates / locale | `jwt_allauth/templates/**`, `jwt_allauth/locale/**` |
| Tests | `tests/**` |
| Docs | `docs/**`, `README.md`, `CONTRIBUTING.md`, `SECURITY.md` |

### Step 3 — Select and launch the agents (IN PARALLEL)

Launch an agent only if the diff touches its domain. When in doubt,
launch it: a wasted pass is cheap, a missed dimension is not.

| Agent (`subagent_type`) | Dimension | Launch it when the diff touches… |
| --- | --- | --- |
| `jwt-allauth-security-reviewer` | Session and token invariants, delegating to allauth | token layer, authentication, endpoints, adapters, shared helpers, startup config, models, templates |
| `jwt-allauth-efficiency-reviewer` | Stateless path, rotation lock, simplicity | token layer, authentication, endpoints, shared helpers, models |
| `jwt-allauth-surface-reviewer` | Public surface, docs, release notes, SEO claims | endpoints, startup config, models, schema, packaging, scaffolder, docs, locale — **or** any change that reads or writes a setting |

Selection notes:

- **Tests only** → usually none of the three. Say so, and point at
  `/code-review` for the tests themselves.
- **Docs only** → `jwt-allauth-surface-reviewer` alone: it checks the
  documentation against the code.
- **Any new or changed setting**, wherever it appears, pulls in
  `jwt-allauth-surface-reviewer` — a setting is public API and owes
  documentation and a release note.
- **Any new endpoint that mints a session** pulls in all three.

**Launch every selected agent in a SINGLE message**, with one `Agent`
tool call each, so they run concurrently. Give each the same PR scope:

```
You are reviewing a pull request. Review EXCLUSIVELY the changes branch
`<head>` introduces against `<resolved base, e.g. origin/develop>`.

- PR diff:       git diff <BASE>...HEAD
- Changed files: <the list from Step 2>
- Commits:       git log <BASE>..HEAD --oneline

Read each changed file IN FULL, not just the diff: the invariants of this
library are decided at module and class level, and the line that breaks
one is often not the line that changed. Apply your own checklist and
return your report by severity, with file:line, evidence and a proposed
fix. Do not review code outside this diff unless you need it to
understand a change (the helper a modified line calls, the setting it
reads, the documentation page it should have updated).
```

Do not reimplement the agents' checklists here. The skill fixes the
**scope**; they own the judgement.

### Step 4 — Aggregate and emit one report

When every agent has finished, **consolidate** — do not re-review:

1. Merge the findings into one list, **deduplicating** those several
   agents raise about the same `file:line` (combine them, noting the
   dimensions that agree — a line flagged by two agents is worth more
   attention, not less).
2. Normalise severity to one scale: **CRITICAL → HIGH → MEDIUM → LOW**.
3. Compute the overall verdict from the worst severity present:
   - any CRITICAL → **BLOCKING (do not merge)**
   - any HIGH → **CHANGES REQUIRED**
   - only MEDIUM/LOW → **APPROVED WITH COMMENTS**
   - nothing → **APPROVED**

Output format:

```
## PR review: <head> → <base>

Files: N changed (+X / −Y) · Commits: M

### Overall verdict
<BLOCKING / CHANGES REQUIRED / APPROVED WITH COMMENTS / APPROVED> — <one sentence>.

### Findings
(ordered CRITICAL → HIGH → MEDIUM → LOW)

#### [CRITICAL] <title>
- Dimension: <Security | Efficiency | Public surface> (agent: <name>)
- File: `path:line`
- Evidence: <quoted code or text>
- Impact: <why it matters>
- Fix: <the concrete correction proposed>

### Per-dimension summary
| Dimension | Agent | Verdict | CRIT | HIGH | MED | LOW |
|-----------|-------|---------|------|------|-----|-----|
| Security | jwt-allauth-security-reviewer | ... | n | n | n | n |
| Efficiency | jwt-allauth-efficiency-reviewer | ... | n | n | n | n |
| Public surface | jwt-allauth-surface-reviewer | ... | n | n | n | n |

### Release readiness
Only when the diff adds or changes a setting, an endpoint or a model:
| Item | Documented | Release notes | README / index claims |
|------|------------|---------------|-----------------------|

### Coverage
- Base: `<resolved base>` · Range: `<BASE>...HEAD` (three-dot / merge base)
- Agents launched: <list> · Skipped: <list + why>
- Not covered here: general correctness and style — run `/code-review`.
```

Report rules:

- Every finding keeps the `file:line` and the evidence from the agent
  that raised it. Do not paraphrase a finding until its anchor is lost.
- Do not inflate severities while aggregating: keep the origin's.
- A clean dimension is reflected in the table, not invented as a finding.
- The **Release readiness** table is the one thing the skill adds on its
  own, and it is a lookup, not a judgement: it restates what the surface
  agent found so a maintainer can see at a glance what the release still
  owes.

## What NOT to do

- ❌ Modify code or documentation — the skill and its agents are
  read-only; they propose fixes, they do not apply them.
- ❌ Use the two-dot range `BASE HEAD`: it drags in changes this branch
  never made. Always `BASE...HEAD`.
- ❌ Review the code yourself, or restate the agents' checklists —
  orchestrate and aggregate; they audit.
- ❌ Launch an agent whose domain the diff does not touch (absent
  reasonable doubt).
- ❌ Duplicate `/code-review` or `/simplify`: correctness and style are
  theirs. Refer them on.
- ❌ Invent findings or verdicts: the report aggregates what came back.
- ❌ Assume a base other than `develop` when no argument is given, or
  guess one when the given base does not exist — ask.
