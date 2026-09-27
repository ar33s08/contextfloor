"""Deterministic transitive markdown-link expansion.

Claude Code pulls every .md target referenced from MEMORY.md into the system
prompt; the same pattern shows up in Hermes MEMORY.md/USER.md. This module
resolves which files that actually implies, following relative markdown links
recursively, with cycle protection and a depth budget.

Only *relative* links to .md files count as floor expansion: absolute http(s)
links are content, not context. Anchor-only links (#sec) stay in the same file.
"""

import hashlib
import os
import re
from pathlib import Path

_MD_LINK = re.compile(r"\[([^\]]*)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
_MAX_DEPTH_DEFAULT = 3
_CACHE = {}


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def read_file(path):
    try:
        return path.read_bytes()
    except OSError:
        return None


def md_links(text):
    """Relative markdown link targets in a string (order preserved)."""
    out = []
    for _label, target in _MD_LINK.findall(text):
        t = target.split("#")[0].strip()
        if not t or t.startswith(("http://", "https://", "mailto:", "file://", "/")):
            continue
        if t.lower().endswith(".md"):
            out.append(t)
    return out


def walk(root, root_bytes=None, max_depth=_MAX_DEPTH_DEFAULT, follow_links=True):
    """Yield (path, bytes, depth, linked_from) for the closure from ``root``.

    Returns a list (stable BFS order). Dead links are reported by the caller
    via ``dead_links``; this function only loads what exists.
    """
    root = Path(root)
    root_bytes = root_bytes if root_bytes is not None else read_file(root)
    if root_bytes is None:
        return [], []

    seen = {root.resolve()}
    order = [(root, root_bytes, 0, None)]
    frontier = [(root, root_bytes)]
    dead = []
    while frontier:
        src, data = frontier.pop(0)
        depth = next(d for p, _b, d, _f in order if p == src)
        if depth >= max_depth or not follow_links:
            continue
        try:
            text = data.decode("utf-8", "replace")
        except Exception:
            continue
        for target in md_links(text):
            resolved = (src.parent / target).resolve()
            if resolved in seen:
                continue
            b = read_file(resolved)
            if b is None:
                dead.append((str(src), target))
                continue
            seen.add(resolved)
            order.append((resolved, b, depth + 1, str(src)))
            frontier.append((resolved, b))
    return order, dead
