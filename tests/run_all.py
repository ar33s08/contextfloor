"""Dependency-free test runner: rediscovers test_* modules and runs test_* fns.

Mirrors the gguf-sentinel contract: the suite must run with no pytest present.
"""

import importlib.util
import pathlib
import sys
import traceback

HERE = pathlib.Path(__file__).resolve().parent


def main():
    sys.path.insert(0, str(HERE))            # so `import _shared` works
    sys.path.insert(0, str(HERE.parent))     # so `import contextfloor` works

    passed = failed = 0
    for path in sorted(HERE.glob("test_*.py")):
        spec = importlib.util.spec_from_file_location(path.name, str(path))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        sys.modules[path.name] = mod
        for fname in sorted(dir(mod)):
            if not fname.startswith("test_"):
                continue
            fn = getattr(mod, fname)
            if not callable(fn):
                continue
            try:
                fn()
                passed += 1
                print(f"  ok   {path.name}::{fname}")
            except Exception:
                failed += 1
                print(f"  FAIL {path.name}::{fname}")
                traceback.print_exc()
    print(f"\n{passed} passed, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
