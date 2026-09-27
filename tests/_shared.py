"""Shared test scaffolding: deterministic, no network, no home dir reads."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.make_fixtures import build_all  # noqa: E402

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


def setup():
    if FIXTURES.is_dir():
        import shutil
        shutil.rmtree(FIXTURES)
    build_all(FIXTURES)


def case(name):
    return FIXTURES / name
