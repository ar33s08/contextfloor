"""Deterministic fixture configs for tests and the corpus demo.

Fixtures are *written by this generator*, never committed as opaque blobs --
same contract-as-demo rule as gguf-sentinel: every number the README shows can
be recomputed from source. Duplicate/chain content is derived from shared
constants so a fixture edit can never silently drift one copy of a "duplicate".
"""

from pathlib import Path

_FILLER = "lorem ipsum dolor sit "
_BLOCK_A = "alpha beta gamma delta "
_BLOCK_B = "epsilon zeta eta theta "
_BLOCK_C = "iota kappa lambda mu "
_BLOCK_D = "nu xi omicron pi "

_MEMORY_ROOT = ("# MEMORY\n\nBig index that loads everything.\n"
                + _FILLER * 150 + "\n- [c1](./C1.md)\n- [gone](./MISSING.md)\n")
_C1 = "# C1\n" + _BLOCK_A * 120 + "\n[c2](./C2.md)\n"
_C2 = "# C2\n" + _BLOCK_B * 120 + "\n[c3](./C3.md)\n"
_C3 = "# C3\n" + _BLOCK_C * 120 + "\n[c4](./C4.md)\n"
_C4 = "# C4\n" + _BLOCK_D * 120 + "\n"
# C6 is byte-identical to C4 by construction (same constant) -> F_DUPLICATE_BYTES,
# and it sits at link depth 3 via C2 -> C5 -> C6 as well.
_C5 = "# C5\n" + _BLOCK_C * 120 + "\n[c6](./C6.md)\n"
_C6 = _C4

_SKELETONS = {
    "lean-hermes/memories/MEMORY.md":
        "# MEMORY\n\n- User is a developer.\n- See [prefs](./PREFS.md) for style.\n",
    "lean-hermes/memories/PREFS.md":
        "# PREFS\n\n- Prefers concise answers.\n",
    "lean-hermes/skills/greetings/SKILL.md":
        "---\nname: greetings\ndescription: Use when greeting the user. Says hi.\n---\n"
        "# Greetings\n\nSay hi politely.\n",

    "bloated-hermes/memories/MEMORY.md": _MEMORY_ROOT,
    "bloated-hermes/memories/C1.md": _C1,
    "bloated-hermes/memories/C2.md": _C2,
    "bloated-hermes/memories/C3.md": _C3,
    "bloated-hermes/memories/C4.md": _C4,
    "bloated-hermes/memories/C5.md": _C5,
    "bloated-hermes/memories/C6.md": _C6,
    "bloated-hermes/skills/vague/SKILL.md":
        "---\nname: Wrong_Name\ndescription: a skill that helps with various things\n---\n"
        "# Vague\n\nDoes stuff.\n",
    "bloated-hermes/skills/hidden/SKILL.md":
        "---\nname: hidden\ndescription: Use when plotting charts." + chr(0x200B) * 2
        + " Invisible here.\n---\n# Hidden\n",

    "broken-skill/skills/orphan/SKILL.md":
        "---\nname: orphan\ndescription: Use when the user asks about orphans.\n---\n"
        "# Orphan\n",
}


def build_all(root):
    root = Path(root)
    for rel, content in _SKELETONS.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("w", encoding="utf-8", newline="\n") as fh:
            fh.write(content)
    return root
