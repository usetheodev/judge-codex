"""The shell must not execute prose that lives inside an inline Python program.

WHY THIS EXISTS
---------------
`python3 -c "..."` is a DOUBLE-quoted shell string. Everything bash expands inside
double quotes still expands there — `$`, `\\`, and backticks — before Python is
handed a single byte. A Python comment naming a function in backticks, which is how
this codebase writes prose everywhere else, becomes a command substitution.

Measured 2026-09-22 against this plugin's own stop hook:

    stop-hook.sh: line 319: re.search: command not found

`re.search` was run as a command and Python received its empty output in place of the
words. It sat in a comment, so only the stderr was polluted — the same construct on a
line that matters changes the program, silently, in a hook that gates every run.

WHY SHELLCHECK DOES NOT CATCH IT FOR US
---------------------------------------
It does see it: SC2006, at severity `style`. The CI runs `-S warning`, and lowering
that to `style` would bury this among hundreds of genuine style notes — which is how
a real finding gets lost in a gate people stop reading. So the dangerous construct
gets its own check, at the severity it deserves.

This test caught its own author twice: the first fix rewrote the command into a
heredoc that `bash -n` accepted and that fed Python the wrong stdin, and the second
explained the defect in a comment that itself used backticks.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

PLUGIN_ROOT = Path(__file__).resolve().parents[1]

#: Every inline program the shell hands to another interpreter as a double-quoted
#: string. Single-quoted (`'...'`) and quoted heredocs (`<<'EOF'`) expand nothing and
#: are the safe forms.
INLINE = re.compile(r'(python3|python|node|ruby|perl)\s+-(c|e)\s+"((?:[^"\\]|\\.)*)"',
                    re.DOTALL)

#: An UNESCAPED backtick. `\`` inside a double-quoted shell string is a literal
#: backtick and is perfectly safe — several plugins write markdown that way on
#: purpose. A detector that flagged those would be a detector somebody turns off,
#: which is how the real one stops being read. Found by running this check across
#: all eighteen plugins: its one hit was an escaped backtick in
#: loop-reference-compare, and it was wrong.
UNESCAPED_BACKTICK = re.compile(r"(?<!\\)`")

SHELL_FILES = sorted(
    p for d in ("hooks", "scripts", "tests")
    for p in (PLUGIN_ROOT / d).rglob("*.sh")
) if (PLUGIN_ROOT / "hooks").is_dir() else []


def _offenders(path: Path) -> list[tuple[int, str, str]]:
    text = path.read_text(encoding="utf-8")
    out = []
    for m in INLINE.finditer(text):
        body = m.group(3)
        line = text[: m.start()].count("\n") + 1
        if UNESCAPED_BACKTICK.search(body):
            out.append((line, "`", "an unescaped backtick becomes a command substitution"))
    return out


@pytest.mark.parametrize("path", SHELL_FILES, ids=lambda p: p.name)
def test_no_shell_metacharacter_inside_an_inline_program(path: Path) -> None:
    bad = _offenders(path)
    assert not bad, "\n".join(
        f"{path.relative_to(PLUGIN_ROOT)}:{line} — {why}. "
        f"The shell expands it before the interpreter sees the source. Drop the "
        f"character, or pass the program on stdin with a quoted heredoc (<<'EOF'), "
        f"which expands nothing."
        for line, _ch, why in bad)


def test_the_detector_finds_the_defect_it_was_written_for(tmp_path: Path) -> None:
    """A check nobody has seen fail is a check nobody has seen work."""
    f = tmp_path / "sample.sh"
    f.write_text(
        'RESULT="$(python3 -c "\n'
        "import re\n"
        "# `re.search` is named in backticks here\n"
        'print(1)\n'
        '")"\n', encoding="utf-8")

    found = _offenders(f)
    assert found and found[0][1] == "`"


def test_the_safe_forms_are_not_flagged(tmp_path: Path) -> None:
    f = tmp_path / "safe.sh"
    f.write_text(
        "python3 - <<'PYEOF'\n# `re.search` is safe in a quoted heredoc\nprint(1)\nPYEOF\n"
        "python3 -c 'import re  # `re.search` is safe in single quotes'\n",
        encoding="utf-8")

    assert not _offenders(f)


def test_an_escaped_backtick_is_not_a_defect(tmp_path: Path) -> None:
    """The false positive this detector produced on its first sweep.

    `\\`` inside a double-quoted shell string is a literal backtick: the shell does
    not substitute it, and several plugins write markdown that way deliberately. A
    detector that called those defects would be turned off, and then the real one
    goes unread too.
    """
    f = tmp_path / "escaped.sh"
    f.write_text(
        'python3 -c "\n'
        "text = 'Cited: \\`internal/worker.go:45\\`'\n"
        'print(text)\n'
        '"\n', encoding="utf-8")

    assert not _offenders(f)
