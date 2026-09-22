"""The program the shell hands to Python must still be a Python program.

WHY THIS EXISTS
---------------
`python3 -c "..."` is a DOUBLE-quoted shell string. Bash processes it before Python
sees a byte, and two of the things it processes are written all the time in ordinary
prose:

    a name in backticks   becomes a command substitution — the words are RUN, and
                          their output (usually empty) is spliced in
    a double quote        CLOSES the string — everything after it is no longer the
                          program

Both were measured in loop-duplication-audit on 2026-09-22, in the SAME comment, one
after the other:

    stop-hook.sh: line 319: re.search: command not found

was the backtick, and it only polluted stderr. The fix for it quoted that very error
message, and the quotes closed the shell string: Python received a truncated program,
printed nothing, and the hook read that empty output as "no completion promise in this
turn". The loop stopped being able to terminate. Four shell suites were red on it, and
the cause read as four separate defects.

WHAT IT COMPARES
----------------
Where BASH would end the string against where the AUTHOR meant it to end. A first
version matched unescaped backticks and could not have found the quote at all: the
regex extracting the program stopped AT the first unescaped quote, so by construction
the captured body never contained one. A detector whose extraction hides the defect it
looks for is worse than none.

It also tried parsing the extracted program and refusing what would not compile. That
went out: the extraction deliberately stops at the author's closing quote, so the
tail is often mid-statement and perfectly fine. A check that fires on its own
truncation is noise, and noise is what gets a gate turned off.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

PLUGIN_ROOT = Path(__file__).resolve().parents[1]

#: The opening of an inline program handed to another interpreter as a DOUBLE-quoted
#: shell string. Single quotes and quoted heredocs expand nothing and are the safe
#: forms, so they are not matched at all.
OPENING = re.compile(r"(?:python3|python)\s+-c\s+\"")

#: Where the AUTHOR closes the string: a line that begins with the quote. That is how
#: every one of these is written, and it is the only way to know where the program was
#: MEANT to end — bash itself ends it at the first unescaped quote, which is precisely
#: the bug. Comparing the two is the check.
#: Two idiomatic spellings, and both are how these are actually written:
#:     a line that begins with the quote            `"` / `")` / `")"`
#:     the quote right after a Python closer        `}))")` / `]")"`
#: The second was added after a sweep: without it, a program whose closing quote
#: follows a bracket looked unterminated, the "program" ran to the end of the file,
#: and every later quote in that file read as a defect.
INTENDED_CLOSE = re.compile(r'^\s*"|[)\]}]\s*"', re.MULTILINE)

#: An unescaped double quote. Inside the program it silently ends the shell string.
UNESCAPED_QUOTE = re.compile(r'(?<!\\)"')

BACKTICK = re.compile(r"(?<!\\)`")


#: The first unescaped quote — where BASH ends the string, whatever the author meant.
BASH_CLOSE = re.compile(r'(?<!\\)"')


def _programs(text: str):
    """Yield (line, source) for each MULTI-LINE inline program, as its author wrote it.

    A one-liner is skipped, and that exclusion is not a gap. `python3 -c "import
    sqlite3"` closes on the same line, so where bash ends the string and where the
    author meant it to end are the same place by construction — there is nothing to
    compare. Including them produced a false positive in nine plugins on the first
    sweep, every one of them a perfectly correct one-liner, and a detector that noisy
    is one somebody turns off.
    """
    for m in OPENING.finditer(text):
        start = m.end()
        bash_close = BASH_CLOSE.search(text, start)
        if bash_close and "\n" not in text[start:bash_close.start()]:
            continue
        close = INTENDED_CLOSE.search(text, start)
        end = close.start() if close else len(text)
        yield text[:start].count("\n") + 1, text[start:end]


def _offenders(path: Path) -> list[tuple[int, str]]:
    out = []
    for line, source in _programs(path.read_text(encoding="utf-8")):
        if UNESCAPED_QUOTE.search(source):
            out.append((line, "an unescaped double quote CLOSES the shell string here, "
                              "so Python receives everything up to it and nothing after "
                              "— a truncated program that may still parse, and whose "
                              "empty output reads like an answer"))
            continue
        if BACKTICK.search(source):
            out.append((line, "an unescaped backtick: bash RUNS those words and splices "
                              "in their output, which is usually nothing"))
            continue
    return out


SHELL_FILES = sorted(
    p for d in ("hooks", "scripts", "tests")
    for p in (PLUGIN_ROOT / d).rglob("*.sh")
) if (PLUGIN_ROOT / "hooks").is_dir() else []


@pytest.mark.parametrize("path", SHELL_FILES, ids=lambda p: p.name)
def test_the_inline_program_survives_the_shell(path: Path) -> None:
    bad = _offenders(path)
    assert not bad, "\n".join(
        f"{path.relative_to(PLUGIN_ROOT)}:{line} — {why}\n"
        f"    Pass the program on stdin with a quoted heredoc, which expands nothing, "
        f"or remove the character."
        for line, why in bad)


# ---------------------------------------------------------------------------
# The detector, against the two defects it was written for
# ---------------------------------------------------------------------------

def test_it_finds_the_quote_that_broke_a_loop(tmp_path: Path) -> None:
    """The one the first version could not see, and the more damaging of the two."""
    f = tmp_path / "quoted.sh"
    f.write_text(
        'RESULT="$(python3 -c "\n'
        'import re\n'
        '# the error was "command not found" on every run\n'
        'print(1)\n'
        '")"\n', encoding="utf-8")

    assert _offenders(f), (
        "an unescaped double quote truncates the program and must be refused")


def test_it_finds_the_backtick(tmp_path: Path) -> None:
    f = tmp_path / "ticked.sh"
    f.write_text(
        'python3 -c "\n'
        'import re\n'
        '# `re.search` discarded the real match\n'
        'print(1)\n'
        '"\n', encoding="utf-8")

    assert _offenders(f)


# ---------------------------------------------------------------------------
# And against what it must NOT call a defect. A detector that cries wolf is turned
# off, and then it cannot report the real one either.
# ---------------------------------------------------------------------------

def test_a_quoted_heredoc_is_safe(tmp_path: Path) -> None:
    f = tmp_path / "heredoc.sh"
    f.write_text("python3 - <<'PYEOF'\n# `re.search` and \"quotes\" are safe here\n"
                 "print(1)\nPYEOF\n", encoding="utf-8")

    assert not _offenders(f)


def test_single_quotes_are_safe(tmp_path: Path) -> None:
    f = tmp_path / "single.sh"
    f.write_text("python3 -c 'import re  # `re.search` is safe in single quotes'\n",
                 encoding="utf-8")

    assert not _offenders(f)


def test_an_escaped_quote_is_not_a_defect(tmp_path: Path) -> None:
    f = tmp_path / "escaped.sh"
    f.write_text('python3 -c "\nprint(\\"hello\\")\n"\n', encoding="utf-8")

    assert not _offenders(f)


def test_a_shell_variable_is_not_a_defect(tmp_path: Path) -> None:
    """Interpolation is the whole reason a program is in double quotes."""
    f = tmp_path / "interp.sh"
    f.write_text('python3 -c "\nimport sys\nprint(sys.argv, \\"$ARG\\")\n" "$ARG"\n',
                 encoding="utf-8")

    assert not _offenders(f)
