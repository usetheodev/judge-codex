# Changelog

All notable changes to this project are recorded in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/) and this project adopts [Semantic Versioning](https://semver.org/).

## [Unreleased]

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
