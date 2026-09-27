"""Verification gate: compile -> import -> behavioural probes -> fixture contract.

Run before every commit; CI runs it first so a broken tree fails fast.
python tools/gate.py
"""

import py_compile
import importlib
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
FAILURES = []


def check(name, fn):
    try:
        fn()
        print(f"  ok   {name}")
    except Exception as exc:
        FAILURES.append((name, exc))
        print(f"  FAIL {name}: {exc!r}")


def main():
    sys.path.insert(0, str(ROOT))

    def _compile():
        bad = []
        for path in ROOT.rglob("**/*.py"):
            if ".venv" in path.parts:
                continue
            try:
                py_compile.compile(str(path), doraise=True)
            except Exception as exc:
                bad.append((str(path), exc))
        if bad:
            raise RuntimeError(f"compile failures: {bad}")
    check("compile", _compile)

    def _import():
        importlib.import_module("contextfloor")
        importlib.import_module("contextfloor.cli")
        importlib.import_module("contextfloor.audit")
        importlib.import_module("contextfloor.tokenizers")
        importlib.import_module("contextfloor.linkgraph")
        importlib.import_module("contextfloor.report")
        importlib.import_module("contextfloor.adapters")
    check("import", _import)

    def _registry_contract():
        from contextfloor.audit import run_audit
        from contextfloor.model import REGISTRY
        import contextfloor.audit as A
        import re as _re
        src = (ROOT / "contextfloor" / "audit.py").read_text(encoding="utf-8")
        emitted = set(_re.findall(
            "Finding.new" + chr(92) + chr(40) + chr(92) + "s*" + chr(34)
            + "(F_" + chr(91) + "A" + chr(45) + "Z_" + chr(93) + "+)" + chr(34), src))
        unknown = emitted - set(REGISTRY)
        assert not unknown, f"audit emits codes absent from REGISTRY: {unknown}"
        for code, (sev, one, why) in REGISTRY.items():
            assert sev in ("error", "warn", "info") and one and why, code
    check("registry<->audit contract", _registry_contract)

    def _fixtures():
        proc = subprocess.run([sys.executable, "tests/run_all.py"], cwd=str(ROOT),
                              capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError("tests/run_all.py failed: " + proc.stdout[-500:])
    check("fixture suite (dep-free)", _fixtures)

    def _cli_smoke():
        from contextfloor.cli import main as cli
        rc = cli(["scan", "generic", "--path", str(ROOT / "fixtures" / "lean-hermes")])
        assert rc == 0, f"lean fixture should scan clean, rc={rc}"
        rc = cli(["scan", "generic", "--path", str(ROOT / "fixtures" / "bloated-hermes")])
        assert rc == 1, f"bloated fixture must gate, rc={rc}"
    check("cli exit-code contract", _cli_smoke)

    print()
    if FAILURES:
        for name, exc in FAILURES:
            print(f"FAILED: {name}")
        return 1
    print("gate: all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
