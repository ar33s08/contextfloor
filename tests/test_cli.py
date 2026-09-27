"""CLI contract: exit codes, formats, and the gate semantics."""

import json
import sys
from pathlib import Path

from _shared import case, setup
setup()

from contextfloor.cli import main


def run(argv):
    return main(argv)


def test_scan_exit_codes():
    assert run(["scan", "generic", "--path", str(case("lean-hermes"))]) == 0
    assert run(["scan", "generic", "--path", str(case("bloated-hermes"),
                                                  )]) != 0


def test_budget_gate_fires():
    assert run(["scan", "generic", "--path", str(case("bloated-hermes")),
                "--budget", "50"]) == 1
    assert run(["scan", "generic", "--path", str(case("lean-hermes")),
                "--budget", "50000"]) == 0


def test_json_schema_stable():
    import io
    import contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        run(["scan", "generic", "--path", str(case("lean-hermes")),
            "--format", "json"])
    doc = json.loads(buf.getvalue())
    assert doc["schema"] == "ctxfloor/0.1"
    assert set(doc["totals"]) == {"gpt", "claude", "gemini"}
    assert doc["items"][0]["sha256"]
    assert {"role", "path", "bytes", "tokens", "depth"} <= set(doc["items"][0])


def test_unknown_agent_is_usage_error():
    try:
        run(["scan", "definitely-not-an-agent"])
        assert False, "should have raised SystemExit"
    except SystemExit as e:
        assert e.code == 2


if __name__ == "__main__":
    print("cli: ok")
