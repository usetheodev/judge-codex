# Changelog

All notable changes to this project are recorded in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/) and this project adopts [Semantic Versioning](https://semver.org/).

### Added

- **A judge seated on a review panel now speaks the panel's language.** These agents
  serve two callers and only one was ever written down: `/judge-codex:<stage>` wants the
  JSON its schema defines, with a `verdict` from the cycle vocabulary; a panel seat wants
  ONE vote — `approve` / `return` / `abstain` — recorded with `cast_vote.py`. The consumer
  seats `judge-codex:*` as the ORTHOGONAL chair of a 2-of-3 panel in DISCOVER, PLAN and
  DESIGN. Measured 2026-09-22 against it:

      $ python3 mechanisms/cycle/cast_vote.py … --verdict SHIPPABLE --reason "…"
      REFUSED: `SHIPPABLE` is not one of approve, return, abstain

  The seat was reachable, convened and briefed, and would have produced a vote the tally
  refuses — an abstention nobody intended, on the one reviewer the other two cannot stand
  in for. Every judge now carries a `## Two callers, two outputs` section naming both, the
  three tokens, and the recorder; the four that could not run a command gained `Bash`; and
  the `cast_vote.py` line names the seat as the roster spells it (`judge-codex:<agent>`),
  because the tally checks the vote against the assignment. The section refuses the obvious
  shortcut in writing: a cycle verdict is a score about structure and the panel is asking a
  different question, so mapping one onto the other mechanically is not answering it.
  `tests/panel-seat.test.sh` checks the instruction is there to obey — it cannot check that
  the model obeys it, and says so.

- **A DESIGN stage, with a `design-judge` and its own schema.** `cycle-design.md` gates the
  phase on a 2-of-3 panel spanning two families, and the consumer's roster had to seat
  `plan-judge` there because this plugin supplied no design judge — an approximation it
  declared rather than glossed. The stage is the first whose artifact is a DIRECTORY and the
  first that reads out of the wiki rather than the dated trail: five drawings under
  `<project>/.squad/wiki/design/`, read together, because a contradiction between two of them
  is invisible to a judge holding either alone. Each file is labelled in the prompt so a
  finding can name its drawing, and a set missing any declared drawing does not resolve at
  all — "absent" and "empty" are different claims about a design, and
  `check_design_completeness.py` already refuses the incomplete set upstream.

  The schema is DESIGN's own vocabulary (`DESIGN_AGREED` / `AWAITING_REVIEW` /
  `NEEDS_REVISION` / `INVALID`), its findings name a drawing rather than a plan section, and
  it carries `scope`: whether there was code to check against, and which drawings were
  actually read. The golden rule makes that scope DERIVED — with no code, R1 is unaskable and
  the judge may not conclude the design is right — so a reader has to be able to tell which
  audit they are holding.

  Verified end to end against the real CLI on a five-drawing probe: `fallback_used: false`,
  `code_on_disk: false` correctly reported, and it found the two defects the fixture actually
  had — a component in D5 that no other drawing covers, and a durability row claiming
  survival with no store named.

## [Unreleased]

## [0.3.2] - 2026-09-22

### Added

- **The inline-Python shell-expansion detector**, propagated from the sibling that
  found the defect: `python3 -c "..."` is a double-quoted shell string, so a backtick
  in the embedded program is executed by bash before the interpreter sees the source.
  Clean here; carried so it stays clean.

### Changed

- **The judge looked for artifacts where the pipeline stopped writing them, and wrote
  its own output where nobody reads.** `STAGE_DISCOVERY_PATHS` held `knowledge-base/…`
  and `.claude/knowledge-base/…` only — the two oldest record roots the cycle ecosystem
  ever used — while the current write root is `<project>/.squad/records/`, with
  `records/` and `.claude/records/` as the documented fallbacks. Measured 2026-09-21 on
  a project using the current layout: `judge --stage plan --slug probe` printed
  `Artifact not found` for a plan that was on disk, for all four stages. This plugin
  fills the ORTHOGONAL seat of a 2-of-3 review panel, so a judge that cannot open the
  document does not weaken the panel — it removes the one reviewer the other two cannot
  stand in for, and the panel records an abstention nobody asked for. All five roots now
  resolve, newest first, and the legacy two stay last so a consumer that never migrated
  keeps its judge. Output moved the same way: it went to `knowledge-base/judge-codex/`
  unconditionally, outside the consumer's declared write root, and now lands in the first
  record root that exists. The `discover` stage also accepts `<slug>-opportunity.md` and
  `discover-opportunity-golden-rule.md` beside the retired `-blueprint` spellings, which
  is what that cycle has written since it was renamed. `tests/artifact-discovery.test.sh`
  covers all four stages on the current layout plus the legacy one, with `codex` stubbed,
  so the table cannot drift from the code again in silence.

- **The four stage judges declared a model that exists on neither side.**
  `model: gpt-5-codex` in an agent frontmatter selects the CLAUDE model that runs the
  sub-agent, and `gpt-5-codex` is not one — while `codex exec --model gpt-5-codex` is
  itself refused on a ChatGPT account (`400 invalid_request_error: not supported when
  using Codex with a ChatGPT account`, measured 2026-09-21 on codex-cli 0.154.0). The
  field pointed at nothing in either direction. It is `sonnet` now, matching the three
  sibling agents: this sub-agent assembles context and invokes the companion, and the
  judging model is Codex's own — resolved from `~/.codex/config.toml`, because the
  companion deliberately omits `--model` so the account default wins.

- **Repository renamed from `judge-codex-plugin-cc` to `judge-codex`,** matching the plugin id it has always declared. The `-plugin-cc` suffix said where the plugin runs, not what it does. New location: `https://github.com/usetheodev/judge-codex`; install with `/plugin marketplace add usetheodev/judge-codex`. GitHub redirects the old URL, so existing clones keep working until their remote is updated.

## [0.1.0] - 2026-06-04

### Added
- **First release** of `judge-codex` — Codex-as-orthogonal-LLM-jury for the `plan` cycle ecosystem.
- 8 slash commands (`/judge-codex:setup`, `:discover`, `:plan`, `:implementation`, `:final`, `:auto`, `:status`, `:help`).
- 7 sub-agents: `judge-codex-jury` (thin forwarder) + 4 stage-judges (`discover-judge`, `plan-judge`, `implementation-judge`, `final-judge`) + `quality-evaluator` (Autoresearch keep/discard gate) + `report-writer` (auto-aggregator).
- 3 skills: `codex-cli-runtime`, `judge-prompting`, `cycle-plan-context`.
- 4 JSON schemas (one per stage) using `plan`'s canonical verdict vocabulary plus final-stage meta-verdicts (`META_DEFECT_FOUND`, `AGGREGATOR_BUG_SUSPECTED`).
- `scripts/codex-companion-judge.mjs` (~350 lines): single-entry runtime that locates artifacts in the consumer repo, assembles prompts (agent system + golden-rule + artifact + anti-anchoring), invokes `codex exec --output-schema --output-last-message --skip-git-repo-check --cd`, validates + persists output.
- `scripts/setup-check.sh` — environment verification (Node ≥ 18.18, codex CLI, login).
- `hooks/hooks.json` — optional Stop hook (off by default).
- Marketplace manifest at `.claude-plugin/marketplace.json` for `/plugin marketplace add` install.
- README documents cycle-aware verdict vocabulary distinct from the binary `approve` / `needs-attention` of generic code-review plugins.

### Verified
- Live integration test against `plan/knowledge-base/plans/harden-fabrication-and-cq-gate-plan.md`:
  - Codex elapsed 87993 ms.
  - Codex verdict `INVALID` (score 49) — caught fabricated ADR reference `D9` that the Claude-side `plan-confidence` M3 v0.1 detector had missed (M3 only inspects `#### Evidence` blocks; `D9` was in plan prose outside that scope).
  - Plus 2 medium-severity soft caps (`goal_not_smart_timebound`, `risks_section_missing`).
  - This is the disagreement-with-Claude scenario the plugin exists to surface.

### Inspired by
- [openai/codex-plugin-cc](https://github.com/openai/codex-plugin-cc) (Apache 2.0) — adopted `.claude-plugin/` layout, codex-companion subprocess pattern, `disable-model-invocation: true` convention, Stop hook. Distinct: cycle-aware (one command per `plan` stage with golden-rule injection), structured verdict vocabulary, review-of-review final stage.
- [paulohenriquevn/loop-code-review](https://github.com/paulohenriquevn/loop-code-review) (MIT) — adopted per-specialist agent layout, Autoresearch keep/discard quality-evaluator gate, report-writer aggregator.
