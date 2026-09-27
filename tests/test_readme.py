"""The README console blocks are a contract: regenerated and diffed every run.

Same rule as gguf-sentinel's demo test: if the output drifts from what the
README shows, this test fails -- the docs can not rot silently.
"""

import io
import re
from contextlib import redirect_stdout

from _shared import case, setup
setup()

README = (case("lean-hermes").parent.parent / "README.md")


def capture(argv):
    from contextfloor.cli import main
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = main(argv)
    return buf.getvalue(), rc


def _trim(text, keep_first=9):
    """README shows TOP ITEMS head-trimmed with an explicit ... marker."""
    lines = text.splitlines()
    out, in_top, top_kept = [], False, 0
    for ln in lines:
        if ln.startswith("  TOP ITEMS"):
            in_top, top_kept = True, 0
            out.append(ln)
            continue
        if in_top:
            if ln.startswith("    ") and "tok  " in ln:
                top_kept += 1
                if top_kept > keep_first:
                    continue
            elif not ln.startswith("    "):
                in_top = False
                out.append("        ...") if top_kept > keep_first else None
        out.append(ln)
    return "\n".join(out)


def test_readme_demo_verbatim():
    src = README.read_text(encoding="utf-8")
    blocks = re.findall(r"```console\n(.*?)```", src, re.S)
    assert blocks, "README lost its console block"
    # block 1: lean scan
    text, rc = capture(["scan", "generic", "--path", str(case("lean-hermes"))])
    shown = blocks[0]
    for needle in ["TOTAL/TURN", " 23 tok  instructions memories/MEMORY.md",
                   "0 error / 0 warn / 0 info"]:
        assert needle in text, f"output lost {needle!r}"
        assert needle in shown, f"README no longer shows {needle!r}"
    assert rc == 0
    # block 2: gate must gate, and README must show the budget finding
    text2, rc2 = capture(["gate", "generic", "--path", str(case("bloated-hermes")),
                          "--budget", "500", "--fail-on", "error"])
    assert rc2 == 1
    assert "F_BUDGET_EXCEEDED" in text2 and "F_BUDGET_EXCEEDED" in shown


if __name__ == "__main__":
    test_readme_demo_verbatim()
    print("readme contract: ok")
