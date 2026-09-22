---
name: cycle-plan-context
description: Locates `plan` cycle artifacts (blueprints, plans, implementation logs, review reports) in the consumer repository. Internal helper for the companion script.
user-invocable: false
---

# cycle-plan-context

How the companion script finds the artifacts to judge in a consumer repo that has the `plan` plugin installed.

## Conventional paths (in order of preference)

For a given `<slug>`, the companion looks under the **consumer repo root** (the cwd when
the slash command was invoked). Every stage resolves the same five record roots, in this
order, and takes the first that holds the artifact:

```
.squad/records/          the current write root
.claude/records/         a plugin install before the root moved
records/                 the standalone kit before the root moved
.claude/knowledge-base/  legacy
knowledge-base/          legacy
```

| Stage | Leaf under the record root | Filename |
|---|---|---|
| `discover` | `discoveries/opportunities/`, then `discoveries/blueprints/` | `<slug>-opportunity.md`, then `<slug>-blueprint.md` |
| `plan` | `plans/` | `<slug>-plan.md` |
| `implementation` | `implementations/` | `<slug>-implementation.md` |
| `final` | `reviews/` | `<slug>-review-*.md` (latest by mtime) |
| `final` (aux) | `reviews/review-<slug>-*/` | per-agent files |

**Why five roots and two filenames.** This table listed `knowledge-base/` and
`.claude/knowledge-base/` only — the two OLDEST locations the pipeline ever used — and
named `<slug>-blueprint.md` for a cycle that now writes `<slug>-opportunity.md`.
Measured 2026-09-21 against a project on the current layout: `judge --stage plan` printed
`Artifact not found` for a plan that was on disk. The legacy roots stay last so a
consumer that never migrated keeps its judge; they are fallbacks, not the default.

`tests/artifact-discovery.test.sh` exercises all four stages on the current layout and
the legacy one, with `codex` stubbed, so this table cannot drift from the code again
without something going red.

## Companion repo detection

The companion script walks up from `cwd` looking for the consumer repo root via these markers (in order):

1. `.git/`
2. `.claude/`
3. `plugin.json` (Claude Code plugin manifest — the `plan` repo signature)
4. `rules/` directory paired with `skills/` (the planning ecosystem layout)
5. `pyproject.toml` / `package.json` as last-resort (not specific to `plan`)

This mirrors the resolver added to `plan`'s `run_structural.py:_find_repo_root_from_plan` (2026-06-04) — same logic.

## Golden-rule resolution

Once the consumer repo root is found, golden-rule files are looked up at:

1. `<root>/rules/<rule>.md`
2. `<root>/.claude/rules/<rule>.md`
3. `<root>/skills/_kit-rules/<rule>.md`
4. `<root>/.claude/skills/_kit-rules/<rule>.md`
5. `${CLAUDE_PLUGIN_ROOT}/templates/golden-rules/<rule>.md` (plugin-bundled fallback)

A stage may name more than one rule, tried in order. `discover` asks for
`discover-opportunity-golden-rule.md` first and `discover-blueprint-golden-rule.md`
second: the contract was renamed between cycle generations, and a judge pointed at the
retired name grades against a file the consumer does not have.

The fallback templates exist so judge-codex works even in repos that have not promoted the rule files from `skills/*/defaults/`.

## Claude-side verdict resolution (for disagreement detection)

The companion looks up the Claude-side verdict (when present) at:

| Stage | Claude-side gate output |
|---|---|
| `discover` | `<record-root>/reviews/<slug>-discover-confidence-*.json` |
| `plan` | `<record-root>/reviews/<slug>-plan-confidence-*.json` |
| `implementation` | `<record-root>/reviews/<slug>-implement-validate-*.md` + `<record-root>/audits/<slug>-code-quality-*.md` |
| `final` | `<record-root>/reviews/<slug>-review-*.md` (the verdict line) |

When found, the verdict is included in the prompt's anti-anchoring section (see `judge-prompting`).

## Output location

All judge-codex output lands in the consumer repo under the FIRST record root that exists (the same list as above — `.squad/records/` on a current project), never at the repo root:

```
<record-root>/judge-codex/<slug>-<stage>-judge-<YYYY-MM-DD>.json
<record-root>/judge-codex/<slug>-<stage>-judge-<YYYY-MM-DD>.md         (human-readable)
<record-root>/judge-codex/<slug>-<stage>-disagreement-<YYYY-MM-DD>.json (when Claude vs Codex differ)
```

The directory is created if missing.
