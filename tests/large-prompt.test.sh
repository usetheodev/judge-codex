#!/usr/bin/env bash
# A judge prompt larger than one argv string still reaches the model.
#
# The companion passed the whole prompt (agent system, golden rule, artifact) as the last
# argument to `codex exec` and to the `claude --print` fallback. Linux caps one argv
# string at 128 KiB (MAX_ARG_STRLEN), so a 141 KB plan failed with E2BIG before any
# model saw it (a consumer, 2026-10-09). Both CLIs read the prompt from stdin when none
# is given on the command line, so it now travels there.
#
# Fake `codex` and `claude` on PATH record how long their argv is and how much arrived on
# stdin; a 200 KB prompt must arrive whole on stdin and nowhere in argv.
set -uo pipefail

PLUGIN_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
mkdir -p "$WORK/bin"
for tool in codex claude; do
  cat > "$WORK/bin/$tool" <<FAKE
#!/usr/bin/env bash
args="\$*"
stdin="\$(cat)"
printf '%s %s\n' "\${#args}" "\${#stdin}" > "$WORK/$tool.sizes"
for ((i = 1; i <= \$#; i++)); do
  if [ "\${!i}" = "--output-last-message" ]; then j=\$((i + 1)); printf '{}' > "\${!j}"; fi
done
[ "$tool" = claude ] && printf '{"result": "{}"}'
exit 0
FAKE
  chmod +x "$WORK/bin/$tool"
done

fails=0
check() {
  local tool="$1" fn="$2"
  PATH="$WORK/bin:$PATH" node --input-type=module -e "
    const m = await import('$PLUGIN_ROOT/scripts/codex-companion-judge.mjs');
    const prompt = 'x'.repeat(200 * 1024);
    const r = m.$fn({ prompt, schemaPath: null, lastMessagePath: '$WORK/last.txt', workdir: '$WORK' });
    if (r.code !== 0) { console.error(r.stderr); process.exit(1); }
  " || { echo "  FAIL — $tool: the call failed"; fails=$((fails + 1)); return; }
  read -r argv_len stdin_len < "$WORK/$tool.sizes"
  if [ "$stdin_len" -eq $((200 * 1024)) ] && [ "$argv_len" -lt 4096 ]; then
    echo "  ok   — $tool: 200 KB prompt arrived on stdin (argv ${argv_len} chars)"
  else
    echo "  FAIL — $tool: argv ${argv_len} chars, stdin ${stdin_len} chars"
    fails=$((fails + 1))
  fi
}

echo "a prompt larger than one argv string reaches the model:"
check codex runCodex
check claude runClaudeFallback
[ "$fails" -eq 0 ] && echo "PASS" || { echo "FAILED: $fails"; exit 1; }
