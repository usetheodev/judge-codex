#!/usr/bin/env bash
# A judge seated on a review panel has to speak the panel's language.
#
# WHY THIS EXISTS
# ---------------
# These agents serve TWO callers and only one was ever written down.
#
#   /judge-codex:<stage>   wants the JSON object its schema defines, whose `verdict`
#                          comes from the cycle vocabulary (SHIPPABLE, NEEDS_REVISION…)
#   a review panel seat    wants ONE vote — approve | return | abstain — recorded with
#                          `cast_vote.py`, plus a reason of at least fifteen words
#
# The consumer's roster seats `judge-codex:discover-judge` / `:plan-judge` as the
# orthogonal chair of a 2-of-3 panel in DISCOVER, PLAN and DESIGN. Measured 2026-09-22
# against that consumer:
#
#   $ python3 mechanisms/cycle/cast_vote.py … --verdict SHIPPABLE --reason "…"
#   REFUSED: `SHIPPABLE` is not one of approve, return, abstain
#
# So the seat was reachable, convened, briefed — and would have produced a vote the
# tally refuses. An abstention nobody intended, on the one reviewer the other two
# cannot stand in for.
#
# WHAT THIS TEST PROVES, AND WHAT IT CANNOT
# -----------------------------------------
# It checks the agent DOCUMENTS: that each judge names both callers, the three vote
# tokens, the recorder, and carries the tool it needs to run it. It cannot prove the
# model obeys the document — no test of a prompt can. It proves the instruction is
# there to obey, which is the half that was missing.
set -uo pipefail

PLUGIN_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
JUDGES=(discover-judge plan-judge implementation-judge final-judge design-judge)

fails=0
pass() { printf '  ok   — %s\n' "$1"; }
fail() { printf '  FAIL — %s\n' "$1"; fails=$((fails + 1)); }

echo "every judge can serve a panel seat:"
for j in "${JUDGES[@]}"; do
  f="$PLUGIN_ROOT/agents/$j.md"

  if [ ! -f "$f" ]; then
    fail "$j: no agent file"
    continue
  fi

  # The three tokens, together. A judge that names only `approve` has not been told
  # how to refuse, and refusing is the whole point of an orthogonal seat.
  missing=""
  for tok in approve return abstain cast_vote.py; do
    grep -q -- "$tok" "$f" || missing="$missing $tok"
  done
  [ -z "$missing" ] && pass "$j names the panel vocabulary and its recorder" \
                    || fail "$j is missing:$missing"

  # `cast_vote.py` is a command. A judge without Bash can reach the verdict and not
  # record it, which the panel reads as a reviewer that never voted.
  if sed -n '1,12p' "$f" | grep -q '^tools:.*Bash'; then
    pass "$j carries Bash, so it can record the vote"
  else
    fail "$j has no Bash in its tools — it could not run cast_vote.py"
  fi

  # Both callers named, so the model knows which output is being asked for.
  if grep -qi "two callers\|panel seat" "$f"; then
    pass "$j distinguishes its two callers"
  else
    fail "$j never says a panel seat is a different caller from the slash command"
  fi
done

echo
if [ "$fails" -gt 0 ]; then echo "$fails check(s) failed"; exit 1; fi
echo "all checks passed"
