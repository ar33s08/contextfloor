"""The README console blocks are a contract: regenerated and diffed every run.

Same rule as gguf-sentinel's upstream-corpus test: environment-dependent
checks SKIP, they do not fail -- a missing optional extra must never
masquerade as a docs or parser regression. The README shows the *exact*
tokenizer variant (``pip install ctxfloor[exact]``); CI installs the extra,
so the gate is real in CI and honest locally.
"""

import io
import re
from contextlib import redirect_stdout

from _shared import case, setup
setup()

README = case("lean-hermes").parent.parent / "README.md"


def capture(argv):
    from contextfloor.cli import main
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = main(argv)
    return buf.getvalue(), rc


def _flex(needle):
    """Needle as a regex tolerant of column-padding differences."""
    return re.compile(re.escape(needle).replace(re.escape(" "), r"\s+"))


def test_readme_demo_verbatim():
    try:
        import tiktoken                      # noqa: F401 -- environment probe
    except ImportError:
        print("  (skipped: ctxfloor[exact] not installed on this machine)")
        return
    blocks = re.findall("```console\n(.*?)```", README.read_text(encoding="utf-8"),
                        re.S)
    assert len(blocks) == 1, "README lost its console contract block"
    shown = blocks[0]

    text, rc = capture(["scan", "generic", "--path", str(case("lean-hermes"))])
    assert rc == 0
    label = "tokenizers: exact(gpt)" + chr(43) + "estimated(claude,gemini)"
    assert label in text, "this machine should be rendering the exact variant"
    assert label in shown, "README drifted from the exact-variant header"
    for needle in ["TOTAL/TURN",
                   " 23 tok  instructions memories/MEMORY.md",
                   " 12 tok  instructions skills/greetings/SKILL.md",
                   " 10 tok  instructions memories/PREFS.md (d1)",
                   "0 error / 0 warn / 0 info"]:
        assert needle in text, f"output lost {needle!r}"
        assert _flex(needle).search(shown), f"README no longer shows {needle!r}"

    text2, rc2 = capture(["gate", "generic", "--path", str(case("bloated-hermes")),
                          "--budget", "500", "--fail-on", "error"])
    assert rc2 == 1, "the bloated fixture must gate; a tool whose gate no longer " \
                     "fires must fail this build"
    for code in ["F_MISSING_LINK", "F_NAME_DIR_MISMATCH", "F_BUDGET_EXCEEDED"]:
        assert code in text2, f"gate lost {code}"
        assert code in shown, f"README dropped {code}"


if __name__ == "__main__":
    test_readme_demo_verbatim()
    print("readme contract: ok")
