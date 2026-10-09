#!/usr/bin/env bash
# The judge has to find the artifact where the pipeline actually writes it.
#
# WHY THIS EXISTS
# ---------------
# `STAGE_DISCOVERY_PATHS` looked for `knowledge-base/plans` and
# `.claude/knowledge-base/plans` — the two OLDEST locations the pipeline ever used.
# The current one is `<project>/.squad/records/plans`, declared in the consumer's own
# `records-location.md` as the single write root, with `records/` and
# `.claude/records/` as the documented fallbacks.
#
# Measured 2026-09-21 against a project on the current layout:
#
#   $ node scripts/codex-companion-judge.mjs judge --stage plan --slug probe-slug
#   Artifact not found for stage=plan slug=probe-slug under <project>
#
# The plan was on disk. The seat this plugin fills is the orthogonal chair of a
# 2-of-3 panel, so a judge that cannot open the document does not weaken the panel —
# it removes the one reviewer the other two cannot replace, and the panel reports an
# abstention nobody asked for.
#
# The same defect on the write side: output went to `knowledge-base/judge-codex/`,
# which the consumer does not read and which sits outside its write root.
#
# `codex` is stubbed on PATH, so this runs offline and spends nothing.
set -uo pipefail

PLUGIN_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPANION="$PLUGIN_ROOT/scripts/codex-companion-judge.mjs"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

fails=0
pass() { printf '  ok   — %s\n' "$1"; }
fail() { printf '  FAIL — %s\n' "$1"; fails=$((fails + 1)); }

# A `codex` that answers instantly with a schema-shaped verdict.
mkdir -p "$WORK/bin"
cat > "$WORK/bin/codex" <<'STUB'
#!/usr/bin/env bash
for arg in "$@"; do
  case "$arg" in
    --output-last-message) next=1 ;;
    *) if [ "${next:-}" = 1 ]; then printf '{"verdict":"SHIPPABLE","findings":[]}' > "$arg"; next=0; fi ;;
  esac
done
printf '{"verdict":"SHIPPABLE","findings":[]}\n'
STUB
chmod +x "$WORK/bin/codex"
export PATH="$WORK/bin:$PATH"

# One project per stage, on the CURRENT layout.
project() {
  local root="$WORK/$1" dir="$2" name="$3"
  mkdir -p "$root/$dir" "$root/rules"
  printf -- '---\nslug: probe\n---\n\n# Artifact\n\n## Goal\nBe found.\n' > "$root/$dir/$name"
  printf 'x\n' > "$root/rules/placeholder.md"
  git -C "$root" init -q . 2>/dev/null
  echo "$root"
}

echo "artifact discovery on the current layout:"
for spec in \
  "plan|.squad/records/plans|probe-plan.md" \
  "discover|.squad/records/discoveries/opportunities|probe-opportunity.md" \
  "implementation|.squad/records/implementations|probe-implementation.md" \
  "final|.squad/records/reviews|probe-review-2026-09-21.md" \
; do
  IFS='|' read -r stage dir name <<< "$spec"
  root="$(project "$stage" "$dir" "$name")"
  out="$(cd "$root" && node "$COMPANION" judge --stage "$stage" --slug probe 2>&1)"
  if grep -q "Artifact not found" <<< "$out"; then
    fail "stage=$stage did not find $dir/$name"
  else
    pass "stage=$stage found $dir/$name"
  fi

  # And the verdict has to land where the consumer reads it.
  if [ -d "$root/.squad/records/judge-codex" ]; then
    pass "stage=$stage wrote under .squad/records/judge-codex"
  elif [ -d "$root/knowledge-base/judge-codex" ]; then
    fail "stage=$stage wrote to knowledge-base/judge-codex — outside the write root"
  else
    fail "stage=$stage wrote no output directory at all"
  fi
done

# DESIGN is the one stage whose artifact is a directory, and it lives in the wiki
# rather than the dated trail: `cycle-design.md` puts the five drawings under
# `<project>/.squad/wiki/design/`. A stage table that only knows single files under
# `records/` cannot reach it, which is why this case is spelled out separately.
echo "design reads the drawing set out of the wiki:"
root="$WORK/design"
mkdir -p "$root/.squad/wiki/design" "$root/rules"
for d in states trust sequence durability system-map; do
  printf '# %s\n\n```mermaid\nflowchart TD\n  A --> B\n```\n' "$d" > "$root/.squad/wiki/design/$d.md"
done
printf 'x\n' > "$root/rules/design-golden-rule.md"
git -C "$root" init -q . 2>/dev/null
out="$(cd "$root" && node "$COMPANION" judge --stage design --slug probe 2>&1)"
# `Artifact not found` is not the only way this fails: an unknown stage never gets
# as far as looking, and its message says something else entirely.
if grep -qE "Artifact not found|Unknown stage" <<< "$out"; then
  fail "stage=design did not reach .squad/wiki/design/ — $(head -1 <<< "$out")"
else
  pass "stage=design found the drawing set"
fi
if [ -d "$root/.squad/records/judge-codex" ]; then
  pass "stage=design wrote under .squad/records/judge-codex"
else
  fail "stage=design wrote no output under the record root"
fi

# The legacy layout must keep working: a consumer that never migrated still has a judge.
echo "legacy layout still resolves:"
root="$(project legacy "knowledge-base/plans" "probe-plan.md")"
out="$(cd "$root" && node "$COMPANION" judge --stage plan --slug probe 2>&1)"
if grep -q "Artifact not found" <<< "$out"; then
  fail "the legacy knowledge-base/plans path stopped resolving"
else
  pass "legacy knowledge-base/plans still resolves"
fi

echo
if [ "$fails" -gt 0 ]; then echo "$fails check(s) failed"; exit 1; fi
echo "all checks passed"
