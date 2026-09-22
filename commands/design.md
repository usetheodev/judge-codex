---
description: Run Codex as orthogonal judge on a `/design` drawing set
argument-hint: '<slug> [--wait|--background]'
disable-model-invocation: true
allowed-tools: Read, Glob, Grep, Bash(node:*), AskUserQuestion
---

# `/judge-codex:design`

> Paths here name the CURRENT durable root (`.squad/wiki/`). The companion resolves
> `.claude/wiki/` and `wiki/` as fallbacks — see the `cycle-plan-context` skill.

Submits the five drawings under `.squad/wiki/design/` to **Codex** as orthogonal jury,
validated against `rules/design-golden-rule.md`.

## Why this stage reads a directory

Every other stage judges ONE document. DESIGN judges five, and they are one system seen
five ways — a contradiction between two of them is invisible to a judge holding either
alone. The companion reads the whole set, labels each file, and the judge names the
drawing it objects to.

| Id | File | What it settles |
|---|---|---|
| D1 | `states.md` | the lifecycle |
| D2 | `trust.md` | where untrusted code stops |
| D3 | `sequence.md` | the call order, failure paths included |
| D4 | `durability.md` | what survives what |
| D5 | `system-map.md` | the components, **derived** from D1–D4 |

A set missing any of them does not resolve. `check_design_completeness.py` refuses an
incomplete set upstream, so the judge is never asked to decide what a missing drawing
means.

## What Codex evaluates

| Question | Source of truth |
|---|---|
| Does a drawing contradict the code? | `design-golden-rule.md § R1` — only askable with code on disk |
| Is an open question drawn as a settled decision? | `§ R2` — the highest-value question, and it needs no code |
| Do the drawings contradict each other? | `§ R3` |
| Is every `PIECE-N` covered, not merely placed? | `cycle-design.md § G-D5` |

It does **not** re-count the structural half — files present, mermaid parses, kind
matches the slot. `check_design_completeness.py` already did, and a judge repeating a
script's answer adds cost and no information.

## Scope is derived, not chosen

With code on disk, the audit is drawing-versus-code. With none, it is internal coherence
only, and the judge may not conclude the design is RIGHT. The verdict carries `scope`
saying which audit you are holding, plus which drawings were actually read.

## Output

```
.squad/records/judge-codex/<slug>-design-judge-<date>.json
```

Schema: `schemas/design-judge-output.schema.json`. Verdict vocabulary is DESIGN's own —
`DESIGN_AGREED`, `AWAITING_REVIEW`, `NEEDS_REVISION`, `INVALID` — not the plan band.

## As a panel seat

`cycle-design.md § G-D8` gates DESIGN on a 2-of-3 panel spanning two model families, and
this is the orthogonal chair. Seated that way, the agent returns a VOTE
(`approve`/`return`/`abstain`) through `cast_vote.py` rather than this JSON — see
`agents/design-judge.md § Two callers, two outputs`. It is the same judgement in the
shape the caller asked for.

## Refuse to run when

- Slug omitted.
- The drawing set is incomplete or absent under any known wiki root.
- `codex` CLI absent.
